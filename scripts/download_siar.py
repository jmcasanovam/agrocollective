#!/usr/bin/env python3
"""
Descarga datos diarios del SiAR, los valida y los carga en InfluxDB.

Endpoint  : GET {BASE_URL}/API/V1/Datos/Diarios/ESTACION
            ?token=...&Id=V17&Id=GR01&FechaInicial=...&FechaFinal=...&DatosCalculados=true
Resultado : serie `weather` (diario) + `weather_weekly` (semanal, calculado aquí
            para datos históricos) + Flux task de downsampling en vivo.

Idempotente: re-ejecutar no duplica puntos (InfluxDB sobreescribe mismo timestamp+tags).

Uso:
    python scripts/download_siar.py [--dry-run]

Vars de entorno (desde .env):
    SIAR_TOKEN, INFLUXDB_HOST, INFLUXDB_PORT, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET_WEATHER

Antes de descargar nada se valida el token SiAR (Info/ACCESOS) y la conexión a
InfluxDB, para poder distinguir un token inválido/caducado de un problema de
conectividad de un rango de fechas sin datos.
"""

import argparse
import logging
import os
import sys
import time
from datetime import date, timedelta
from urllib.parse import urlencode

import httpx
import pandas as pd
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, Task, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
# httpx loguea la URL completa incluyendo el token, lo silenciamos
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# ------------------------------------------------------------------ #
# Constantes                                                          #
# ------------------------------------------------------------------ #

BASE_URL    = "https://servicio.mapa.gob.es/siarapi"
ENDPOINT    = f"{BASE_URL}/API/V1/Datos/Diarios/ESTACION"
DATE_START  = date(2025, 6, 23)   # Fecha mínima autorizada por SiAR para el token actual

STATION_REGION = {"V17": "VALENCIA", "GR01": "BAZA"}

# SiAR field  ->  InfluxDB field
FIELD_MAP = {
    "TempMedia":     "air_temp",
    "HumedadMedia":  "relative_humidity",
    "Precipitacion": "precipitation",
    "TempSuelo1":    "soil_temp",
    "EtPMon":        "eto",
    "PePMon":        "pe",
    "TempMax":       "air_temp_max",
    "TempMin":       "air_temp_min",
    "HumedadMax":    "relative_humidity_max",
    "humedadMin":    "relative_humidity_min",
}

DAILY_ONLY_FIELDS = {"air_temp_max", "air_temp_min", "relative_humidity_max", "relative_humidity_min"}

SUM_FIELDS  = {"eto", "pe", "precipitation"}   # suma semanal
MEAN_FIELDS = {"air_temp", "relative_humidity"} # media semanal

ETO_WARN_MAX = 12.0  # mm/día: valor sospechoso si se supera
MAX_INTERP_GAP = 7   # días: huecos <= esto se interpolan linealmente

FLUX_TASK_NAME = "weather_weekly_downsampling"


# ------------------------------------------------------------------ #
# Configuración                                                        #
# ------------------------------------------------------------------ #

def load_config(dry_run: bool = False) -> dict:
    always_required = ["SIAR_TOKEN"]
    influx_required = ["INFLUXDB_HOST", "INFLUXDB_PORT", "INFLUXDB_TOKEN", "INFLUXDB_ORG", "INFLUXDB_BUCKET_WEATHER"]
    required = always_required if dry_run else always_required + influx_required
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        log.error("Variables de entorno faltantes: %s", ", ".join(missing))
        sys.exit(1)

    cfg: dict = {"siar_token": os.environ["SIAR_TOKEN"]}
    if not dry_run:
        cfg.update({
            "influx_url":    f"http://{os.environ['INFLUXDB_HOST']}:{os.environ['INFLUXDB_PORT']}",
            "influx_token":  os.environ["INFLUXDB_TOKEN"],
            "influx_org":    os.environ["INFLUXDB_ORG"],
            "influx_bucket": os.environ["INFLUXDB_BUCKET_WEATHER"],
        })
    return cfg


def _is_date_range_error(body: dict | None) -> bool:
    """
    SiAR responde HTTP 403 tanto para token inválido como para 'fecha inicial
    anterior a la fecha mínima autorizada para este token'. Este último caso
    es una restricción de rango permanente para esa fecha, no un problema de
    token: su mensaje siempre incluye 'Fecha Mínima' (y, confusamente, la
    palabra "token" como parte de la URL de ejemplo que devuelve, por lo que
    NO se puede usar esa palabra para distinguir ambos casos).
    """
    if not body:
        return False
    msg = str(body.get("MensajeRespuesta") or "").lower()
    return "fecha mínima" in msg or "fecha minima" in msg


def check_siar_token(cfg: dict):
    """
    Valida el token SiAR contra Info/ACCESOS antes de descargar nada.
    Así, si el token es inválido/caducado, se detecta de inmediato en vez de
    fallar a mitad de una descarga larga con un error genérico.
    """
    url = f"{BASE_URL}/API/V1/Info/ACCESOS?{urlencode({'token': cfg['siar_token']})}"
    try:
        resp = httpx.get(url, timeout=30)
    except httpx.RequestError as exc:
        log.error("No se pudo contactar el servicio SiAR para validar el token: %s", type(exc).__name__)
        sys.exit(1)

    try:
        body = resp.json()
    except ValueError:
        body = None

    if resp.status_code == 200 and isinstance((body or {}).get("datos"), list) and body["datos"]:
        info = body["datos"][0]
        log.info(
            "Token SiAR OK. Uso hoy: %s/%s peticiones · %s/%s registros.",
            info.get("NumAccesosDiaActual"), info.get("MaxAccesosDia"),
            info.get("RegistrosAcumuladosDia"), info.get("MaxRegistrosDia"),
        )
        return

    if resp.status_code in (401, 403):
        log.error("Token de SiAR inválido o caducado (HTTP %s). Verifica SIAR_TOKEN en .env.", resp.status_code)
        sys.exit(1)

    log.error(
        "No se pudo validar el token de SiAR (HTTP %s): %s",
        resp.status_code, body if body is not None else resp.text[:200],
    )
    sys.exit(1)


def check_influx_connection(cfg: dict):
    """Comprueba que InfluxDB es alcanzable antes de seguir, para no confundir
    un problema de conectividad con 'no hay datos previos'."""
    client = InfluxDBClient(
        url=cfg["influx_url"],
        token=cfg["influx_token"],
        org=cfg["influx_org"],
    )
    try:
        if not client.ping():
            log.error("InfluxDB en %s no respondió al ping.", cfg["influx_url"])
            sys.exit(1)
    except Exception as exc:
        log.error(
            "No se pudo conectar a InfluxDB en %s (%s): %s",
            cfg["influx_url"], type(exc).__name__, exc,
        )
        log.error("Verifica INFLUXDB_HOST, INFLUXDB_PORT, INFLUXDB_TOKEN e INFLUXDB_ORG en .env.")
        sys.exit(1)
    finally:
        client.close()


def ensure_bucket_exists(cfg: dict):
    """Asegura que el bucket de InfluxDB exista, creándolo si es necesario."""
    client = InfluxDBClient(
        url=cfg["influx_url"],
        token=cfg["influx_token"],
        org=cfg["influx_org"],
    )
    try:
        buckets_api = client.buckets_api()
        bucket_name = cfg["influx_bucket"]
        existing = buckets_api.find_bucket_by_name(bucket_name)
        if not existing:
            orgs_api = client.organizations_api()
            orgs = orgs_api.find_organizations(org=cfg["influx_org"])
            if not orgs:
                log.error("No se encontró la organización de InfluxDB '%s'", cfg["influx_org"])
                sys.exit(1)
            buckets_api.create_bucket(bucket_name=bucket_name, org_id=orgs[0].id)
            log.info("Creado bucket de InfluxDB '%s'.", bucket_name)
    except Exception as exc:
        log.warning("No se pudo verificar/crear el bucket en InfluxDB: %s", exc)
    finally:
        client.close()


def get_latest_weather_date(cfg: dict) -> date | None:
    """
    Consulta InfluxDB para obtener la fecha del último registro de weather.
    Devuelve None solo si la consulta tuvo éxito y no hay ningún registro
    desde DATE_START. Si la consulta falla (conexión, auth, etc.) aborta en
    vez de devolver None, para no confundirlo con "no hay datos previos" y
    disparar una redescarga completa por un fallo transitorio de InfluxDB.
    """
    client = InfluxDBClient(
        url=cfg["influx_url"],
        token=cfg["influx_token"],
        org=cfg["influx_org"],
    )
    try:
        query_api = client.query_api()
        query = f'''
        from(bucket: "{cfg['influx_bucket']}")
          |> range(start: {DATE_START.isoformat()}T00:00:00Z)
          |> filter(fn: (r) => r._measurement == "weather")
          |> last()
        '''
        tables = query_api.query(query)
    except Exception as exc:
        log.error("No se pudo consultar InfluxDB para obtener la última fecha (%s): %s", type(exc).__name__, exc)
        sys.exit(1)
    finally:
        client.close()

    latest_dt = None
    for table in tables:
        for record in table.records:
            t = record.get_time()
            if t:
                latest_dt = t.date()
    return latest_dt


# ------------------------------------------------------------------ #
# Descarga                                                            #
# ------------------------------------------------------------------ #

_CHUNK_DAYS = 28  # API SiAR limita el rango por petición; 28 días es seguro


_RETRY_DELAYS = [30, 60, 120]  # backoff en segundos ante 429/403 por rate-limit


def _fetch_chunk(cfg: dict, chunk_start: date, chunk_end: date) -> list:
    """Descarga un chunk de días con retry ante rate-limit. Nunca loguea el token."""
    qs = urlencode([
        ("token",           cfg['siar_token']),
        ("Id",              "V17"),
        ("Id",              "GR01"),
        ("FechaInicial",    chunk_start.isoformat()),
        ("FechaFinal",      chunk_end.isoformat()),
        ("DatosCalculados", "true"),
    ], doseq=True)
    url = f"{ENDPOINT}?{qs}"
    log.info("  chunk %s → %s", chunk_start, chunk_end)

    for attempt, delay in enumerate([0] + _RETRY_DELAYS, start=1):
        if delay:
            log.info("  rate-limit: esperando %ds antes del reintento %d…", delay, attempt)
            time.sleep(delay)
        try:
            resp = httpx.get(url, timeout=60)
        except httpx.RequestError as exc:
            log.error("Error de red al contactar SiAR: %s", type(exc).__name__)
            sys.exit(1)

        try:
            body = resp.json()
        except ValueError:
            body = None

        if resp.status_code == 200:
            msg = (body or {}).get("MensajeRespuesta")
            if msg:
                log.error("SiAR error en chunk %s→%s: %s", chunk_start, chunk_end, msg)
                sys.exit(1)
            return (body or {}).get("datos", [])

        if resp.status_code == 401:
            log.error(
                "Token de SiAR inválido o caducado (HTTP 401) en chunk %s→%s. Verifica SIAR_TOKEN en .env.",
                chunk_start, chunk_end,
            )
            sys.exit(1)

        if resp.status_code == 403 and _is_date_range_error(body):
            log.error(
                "SiAR rechazó %s por estar fuera del rango de fechas autorizado para este token "
                "(HTTP 403, no es un problema de token): %s",
                chunk_start, (body or {}).get("MensajeRespuesta"),
            )
            log.error(
                "Ajusta DATE_START en scripts/download_siar.py a una fecha más reciente, "
                "o solicita a SiAR ampliar el histórico disponible para este token."
            )
            sys.exit(1)

        if resp.status_code in (403, 429) and attempt <= len(_RETRY_DELAYS):
            continue  # reintenta con el siguiente delay (posible rate-limit)

        log.error(
            "HTTP %s al contactar SiAR (chunk %s→%s): %s",
            resp.status_code, chunk_start, chunk_end, body if body is not None else resp.text[:200],
        )
        sys.exit(1)

    log.error("Agotados los reintentos para chunk %s→%s.", chunk_start, chunk_end)
    sys.exit(1)


def download_siar(cfg: dict, start_date: date, end_date: date) -> pd.DataFrame:
    """
    Descarga datos diarios en chunks de 28 días (límite de la API SiAR).
    Nunca loguea la URL completa ni el token.
    """
    log.info("GET %s (chunks de %d días, %s → %s)", ENDPOINT, _CHUNK_DAYS, start_date, end_date)

    all_datos: list = []
    chunk_start = start_date
    while chunk_start <= end_date:
        chunk_end = min(chunk_start + timedelta(days=_CHUNK_DAYS - 1), end_date)
        all_datos.extend(_fetch_chunk(cfg, chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(days=1)
        if chunk_start <= end_date:
            time.sleep(15)  # evita rate-limit de la API SiAR (~1 req/10s)

    if not all_datos:
        log.warning("La respuesta SiAR no contiene registros.")
        return pd.DataFrame()

    log.info("Registros recibidos total: %d", len(all_datos))
    return pd.DataFrame(all_datos)


# ------------------------------------------------------------------ #
# Validación                                                          #
# ------------------------------------------------------------------ #

def validate_station(df: pd.DataFrame, station_id: str, start_date: date, end_date: date) -> pd.DataFrame:
    """Valida, reporta y devuelve el DataFrame de la estación, o aborta."""
    log.info("")
    log.info("** Validación %s (%s) **********************", station_id, STATION_REGION[station_id])

    if df.empty:
        log.warning("Sin datos para %s en el rango solicitado.", station_id)
        return df

    df = df.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
    df = df.sort_values("Fecha").reset_index(drop=True)

    expected_days = (end_date - start_date).days + 1
    n = len(df)
    log.info("  Registros           : %d (esperados %d)", n, expected_days)
    log.info("  Rango real          : %s → %s", df["Fecha"].iloc[0], df["Fecha"].iloc[-1])

    # Huecos
    all_dates = {start_date + timedelta(days=i) for i in range(expected_days)}
    gaps = sorted(all_dates - set(df["Fecha"]))

    if gaps:
        max_run = _max_consecutive_days(gaps)
        log.warning("  Días ausentes       : %d  %s", len(gaps), _fmt_gaps(gaps))
        if max_run > MAX_INTERP_GAP:
            log.error(
                "  Hueco largo de %d días consecutivos: revisar manualmente. Abortando.",
                max_run,
            )
            sys.exit(1)
        log.info("  Hueco máximo %d día(s) ≤ %d → se interpolará.", max_run, MAX_INTERP_GAP)
    else:
        log.info("  Huecos              : ninguno")

    # Nulos por campo
    log.info("  Nulos por campo:")
    for siar_field, influx_field in FIELD_MAP.items():
        if influx_field in DAILY_ONLY_FIELDS:
            continue
        if siar_field not in df.columns:
            log.info("    %-15s → campo ausente en respuesta", siar_field)
            continue
        nulls = int(df[siar_field].isna().sum())
        pct = 100.0 * nulls / n
        marker = " ⚠" if (nulls > 0 and siar_field == "EtPMon") or pct > 20 else ""
        log.info("    %-15s %3d / %d (%.0f%%)%s", siar_field, nulls, n, pct, marker)

    if "EtPMon" not in df.columns or df["EtPMon"].isna().all():
        log.error(
            "  EtPMon completamente nula: ¿falta DatosCalculados=true? Abortando."
        )
        sys.exit(1)

    # Magnitud de ETo
    eto = df["EtPMon"].dropna()
    log.info(
        "  EtPMon              : media=%.2f  máx=%.2f  mín=%.2f  mm/día",
        eto.mean(), eto.max(), eto.min(),
    )
    if eto.max() > ETO_WARN_MAX:
        log.warning("  EtPMon máximo %.2f > %.1f mm/día: verificar unidades.", eto.max(), ETO_WARN_MAX)

    return df


def _max_consecutive_days(days: list[date]) -> int:
    if not days:
        return 0
    max_run = run = 1
    for i in range(1, len(days)):
        run = run + 1 if (days[i] - days[i - 1]).days == 1 else 1
        max_run = max(max_run, run)
    return max_run


def _fmt_gaps(gaps: list[date]) -> str:
    shown = [str(d) for d in gaps[:5]]
    rest = f" (+{len(gaps)-5} más)" if len(gaps) > 5 else ""
    return str(shown) + rest


# ------------------------------------------------------------------ #
# Interpolación de huecos cortos                                      #
# ------------------------------------------------------------------ #

def interpolate_gaps(df: pd.DataFrame, station_id: str, start_date: date, end_date: date) -> pd.DataFrame:
    """Inserta filas para días ausentes e interpola linealmente (limit=MAX_INTERP_GAP)."""
    if df.empty:
        return df
    expected_days = (end_date - start_date).days + 1
    full_range = pd.DataFrame(
        {"Fecha": [start_date + timedelta(days=i) for i in range(expected_days)]}
    )
    df = full_range.merge(df, on="Fecha", how="left")

    numeric = df.select_dtypes(include="number").columns.tolist()
    before = int(df[numeric].isna().sum().sum())
    if before:
        df[numeric] = df[numeric].interpolate(
            method="linear", limit=MAX_INTERP_GAP, limit_direction="both"
        )
        after = int(df[numeric].isna().sum().sum())
        log.info("  [%s] Interpolados: %d valores (quedan nulos: %d)", station_id, before - after, after)

    return df


# ------------------------------------------------------------------ #
# Puntos InfluxDB: weather (diario)                                  #
# ------------------------------------------------------------------ #

def to_daily_points(df: pd.DataFrame, station_id: str) -> list:
    region = STATION_REGION[station_id]
    points = []
    for _, row in df.iterrows():
        p = (
            Point("weather")
            .tag("region_code", region)
            .tag("siar_station_code", station_id)
            .time(pd.Timestamp(row["Fecha"]).to_pydatetime(), WritePrecision.S)
        )
        for siar_field, influx_field in FIELD_MAP.items():
            val = row.get(siar_field)
            if pd.notna(val):
                p = p.field(influx_field, float(val))
        points.append(p)
    return points


# ------------------------------------------------------------------ #
# Puntos InfluxDB: weather_weekly (histórico calculado )             #
# ------------------------------------------------------------------ #

def to_weekly_points(df: pd.DataFrame, station_id: str) -> list:
    """
    Agrega a semanas (lunes→domingo, label en lunes).
    Mismos límites que measurements_weekly de sensores.
    """
    region = STATION_REGION[station_id]
    df = df.copy()
    df.index = pd.to_datetime(df["Fecha"])

    # W-MON: semanas que empiezan el lunes
    groups = df.resample("W-MON", label="left", closed="left")

    points = []
    for week_ts, group in groups:
        if group.empty:
            continue
        p = (
            Point("weather_weekly")
            .tag("region_code", region)
            .tag("siar_station_code", station_id)
            .time(week_ts.to_pydatetime(), WritePrecision.S)
        )
        for siar_field, influx_field in FIELD_MAP.items():
            if influx_field in DAILY_ONLY_FIELDS:
                continue
            if siar_field not in group.columns:
                continue
            series = group[siar_field].dropna()
            if series.empty:
                continue
            val = series.sum() if influx_field in SUM_FIELDS else series.mean()
            p = p.field(influx_field, float(val))
        points.append(p)
    return points


# ------------------------------------------------------------------ #
# Escritura en InfluxDB                                               #
# ------------------------------------------------------------------ #

def write_influx(points: list, cfg: dict, label: str, dry_run: bool = False):
    if not points:
        log.info("  [%s] 0 puntos: nada que escribir.", label)
        return
    if dry_run:
        log.info("  [dry-run] %s: %d puntos listos (no se escriben).", label, len(points))
        return

    client = InfluxDBClient(
        url=cfg["influx_url"],
        token=cfg["influx_token"],
        org=cfg["influx_org"],
    )
    try:
        client.write_api(write_options=SYNCHRONOUS).write(
            bucket=cfg["influx_bucket"], record=points
        )
        log.info("  %s: %d puntos escritos.", label, len(points))
    finally:
        client.close()


# ------------------------------------------------------------------ #
# Flux task: downsampling semanal en vivo                             #
# ------------------------------------------------------------------ #

_FLUX_TASK = """\
option task = {{name: "{name}", every: 1d, offset: 1h}}

bucket = "{bucket}"

sumFields = ["eto", "pe", "precipitation"]
meanFields = ["air_temp", "relative_humidity"]

sumData = from(bucket: bucket)
    |> range(start: -14d)
    |> filter(fn: (r) => r._measurement == "weather")
    |> filter(fn: (r) => contains(value: r._field, set: sumFields))
    |> aggregateWindow(every: 7d, fn: sum, createEmpty: false, offset: -3d)
    |> set(key: "_measurement", value: "weather_weekly")

meanData = from(bucket: bucket)
    |> range(start: -14d)
    |> filter(fn: (r) => r._measurement == "weather")
    |> filter(fn: (r) => contains(value: r._field, set: meanFields))
    |> aggregateWindow(every: 7d, fn: mean, createEmpty: false, offset: -3d)
    |> set(key: "_measurement", value: "weather_weekly")

union(tables: [sumData, meanData])
    |> to(bucket: bucket)
"""


def setup_weekly_task(cfg: dict, dry_run: bool = False):
    """Crea o actualiza la Flux task de downsampling semanal en InfluxDB."""
    bucket = cfg.get("influx_bucket", "<bucket>")
    flux = _FLUX_TASK.format(name=FLUX_TASK_NAME, bucket=bucket)

    if dry_run:
        log.info("[dry-run] Flux task no creada. Script Flux:")
        log.info(flux)
        return

    client = InfluxDBClient(
        url=cfg["influx_url"],
        token=cfg["influx_token"],
        org=cfg["influx_org"],
    )
    try:
        api = client.tasks_api()
        existing = [t for t in api.find_tasks() if t.name == FLUX_TASK_NAME]
        if existing:
            task = existing[0]
            task.flux = flux
            api.update_task(task)
            log.info("Flux task '%s' actualizada.", FLUX_TASK_NAME)
        else:
            orgs = client.organizations_api().find_organizations(org=cfg["influx_org"])
            if not orgs:
                raise RuntimeError(f"Organización '{cfg['influx_org']}' no encontrada")
            # No usamos create_task_every: antepone su propio "option task = {...}"
            # al flux dado, y el nuestro ya incluye esa cabecera -> "multiple task
            # options defined". Con create_task() el flux se envía tal cual.
            api.create_task(Task(id=0, name=FLUX_TASK_NAME, org_id=orgs[0].id, status="active", flux=flux))
            log.info("Flux task '%s' creada.", FLUX_TASK_NAME)
    except Exception as exc:
        log.warning(
            "No se pudo configurar la Flux task automáticamente (%s). "
            "Créala manualmente en InfluxDB con el script Flux mostrado arriba.",
            exc,
        )
        log.info(flux)
    finally:
        client.close()




# ------------------------------------------------------------------ #
# Main                                                                #
# ------------------------------------------------------------------ #

def main():
    parser = argparse.ArgumentParser(
        description="Descarga SiAR (diario) y carga en InfluxDB."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Ejecuta validación completa sin escribir en InfluxDB.",
    )
    args = parser.parse_args()

    cfg = load_config(dry_run=args.dry_run)

    # 0. Validaciones previas: fallar rápido y con un mensaje claro si el
    #    problema es el token de SiAR o la conexión a InfluxDB, en vez de un
    #    error genérico a mitad de la descarga.
    check_siar_token(cfg)

    latest_date = None
    if not args.dry_run:
        check_influx_connection(cfg)
        ensure_bucket_exists(cfg)
        latest_date = get_latest_weather_date(cfg)

    requested_end = date.today()
    if latest_date:
        log.info("Última fecha registrada en InfluxDB desde %s: %s", DATE_START, latest_date)
        if latest_date >= requested_end:
            log.info("Los datos de clima de SiAR ya están completos hasta %s. Omitiendo descarga.", requested_end)
            setup_weekly_task(cfg, dry_run=False)
            sys.exit(0)
        # Usamos la última fecha como punto de partida (1 día de solape para anclaje de interpolación)
        start_date = latest_date
    else:
        log.info("No se encontraron datos desde %s en InfluxDB. Descargando histórico completo.", DATE_START)
        start_date = DATE_START

    if start_date >= requested_end:
        log.info("Rango de descarga vacío (%s -> %s). Omitiendo.", start_date, requested_end)
        setup_weekly_task(cfg, dry_run=False)
        sys.exit(0)

    # 1. Descarga. SiAR puede no tener publicados aún los datos de hoy: se
    #    pide hasta hoy pero la fecha final efectiva se recorta más abajo,
    #    por estación, a la última fecha con datos realmente recibida.
    df_all = download_siar(cfg, start_date, requested_end)

    if df_all.empty:
        log.info("No hay nuevos datos para descargar y procesar. Omitiendo.")
        setup_weekly_task(cfg, dry_run=False)
        sys.exit(0)

    # Columna de estación en la respuesta del SiAR
    station_col = next((c for c in ("Estacion", "Id", "id", "estacion") if c in df_all.columns), None)
    if station_col is None:
        log.error("No se encontró columna de estación en la respuesta SiAR. Columnas: %s", list(df_all.columns))
        sys.exit(1)

    all_daily: list = []
    all_weekly: list = []

    for station_id in STATION_REGION:
        df_st = df_all[df_all[station_col] == station_id].copy()
        if df_st.empty:
            log.info("  [%s] Sin datos nuevos en el rango. Omitiendo.", station_id)
            continue

        # Fecha final efectiva = última fecha con datos recibidos (puede ser
        # anterior a hoy si SiAR aún no ha publicado el día actual).
        df_st["Fecha"] = pd.to_datetime(df_st["Fecha"]).dt.date
        station_end = df_st["Fecha"].max()
        if station_end < requested_end:
            log.info(
                "  [%s] SiAR no tiene datos hasta %s todavía; usando %s como fecha final.",
                station_id, requested_end, station_end,
            )

        # 2. Validar
        df_st = validate_station(df_st, station_id, start_date, station_end)

        # 3. Interpolar huecos cortos
        df_st = interpolate_gaps(df_st, station_id, start_date, station_end)

        # 4. Construir puntos
        daily  = to_daily_points(df_st, station_id)
        weekly = to_weekly_points(df_st, station_id)

        log.info(
            "  [%s] %d puntos diarios · %d semanas",
            station_id, len(daily), len(weekly),
        )
        all_daily.extend(daily)
        all_weekly.extend(weekly)

    log.info("")
    log.info("── Escritura en InfluxDB ───────────────────────────────")
    write_influx(all_daily,  cfg, label="weather",         dry_run=args.dry_run)
    write_influx(all_weekly, cfg, label="weather_weekly",  dry_run=args.dry_run)

    log.info("")
    log.info("── Flux task downsampling semanal ──────────────────────")
    setup_weekly_task(cfg, dry_run=args.dry_run)

    log.info("")
    log.info("Done.")


if __name__ == "__main__":
    main()
