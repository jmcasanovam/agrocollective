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
    SIAR_TOKEN, INFLUXDB_HOST, INFLUXDB_PORT, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET
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
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
# httpx loguea la URL completa incluyendo el token — lo silenciamos
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# ------------------------------------------------------------------ #
# Constantes                                                          #
# ------------------------------------------------------------------ #

BASE_URL    = "https://servicio.mapa.gob.es/siarapi"
ENDPOINT    = f"{BASE_URL}/API/V1/Datos/Diarios/ESTACION"
DATE_START  = date(2025, 6, 28)   # token SiAR autorizado desde ~12 meses atrás
DATE_END    = date(2025, 10, 31)
EXPECTED_DAYS = (DATE_END - DATE_START).days + 1  # 126

STATION_REGION = {"V17": "VALENCIA", "GR01": "BAZA"}

# SiAR field  ->  InfluxDB field
FIELD_MAP = {
    "TempMedia":     "air_temp",
    "HumedadMedia":  "relative_humidity",
    "Precipitacion": "precipitation",
    "TempSuelo1":    "soil_temp",
    "EtPMon":        "eto",
    "PePMon":        "pe",
}

SUM_FIELDS  = {"eto", "pe", "precipitation"}   # suma semanal
MEAN_FIELDS = {"air_temp", "relative_humidity"} # media semanal

ETO_WARN_MAX = 12.0  # mm/día: valor sospechoso si se supera
MAX_INTERP_GAP = 2   # días: huecos <= esto se interpolan linealmente

FLUX_TASK_NAME = "weather_weekly_downsampling"


# ------------------------------------------------------------------ #
# Configuración                                                        #
# ------------------------------------------------------------------ #

def load_config(dry_run: bool = False) -> dict:
    always_required = ["SIAR_TOKEN"]
    influx_required = ["INFLUXDB_HOST", "INFLUXDB_PORT", "INFLUXDB_TOKEN", "INFLUXDB_ORG", "INFLUXDB_BUCKET"]
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
            "influx_bucket": os.environ["INFLUXDB_BUCKET"],
        })
    return cfg


# ------------------------------------------------------------------ #
# Descarga                                                            #
# ------------------------------------------------------------------ #

_CHUNK_DAYS = 28  # API SiAR limita el rango por petición; 28 días es seguro


_RETRY_DELAYS = [30, 60, 120]  # backoff en segundos ante 429/403 por rate-limit


def _fetch_chunk(cfg: dict, chunk_start: date, chunk_end: date) -> list:
    """Descarga un chunk de días con retry ante rate-limit. Nunca loguea el token."""
    other_qs = urlencode([
        ("Id",              "V17"),
        ("Id",              "GR01"),
        ("FechaInicial",    chunk_start.isoformat()),
        ("FechaFinal",      chunk_end.isoformat()),
        ("DatosCalculados", "true"),
    ], doseq=True)
    url = f"{ENDPOINT}?token={cfg['siar_token']}&{other_qs}"
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

        if resp.status_code == 200:
            body = resp.json()
            msg = body.get("MensajeRespuesta")
            if msg:
                log.error("SiAR error en chunk %s→%s: %s", chunk_start, chunk_end, msg)
                sys.exit(1)
            return body.get("datos", [])

        if resp.status_code in (403, 429) and attempt <= len(_RETRY_DELAYS):
            continue  # reintenta con el siguiente delay

        log.error("HTTP %s al contactar SiAR (chunk %s→%s)", resp.status_code, chunk_start, chunk_end)
        sys.exit(1)

    log.error("Agotados los reintentos para chunk %s→%s.", chunk_start, chunk_end)
    sys.exit(1)


def download_siar(cfg: dict) -> pd.DataFrame:
    """
    Descarga datos diarios en chunks de 28 días (límite de la API SiAR).
    Nunca loguea la URL completa ni el token.
    """
    log.info("GET %s (chunks de %d días, %s → %s)", ENDPOINT, _CHUNK_DAYS, DATE_START, DATE_END)

    all_datos: list = []
    chunk_start = DATE_START
    while chunk_start <= DATE_END:
        chunk_end = min(chunk_start + timedelta(days=_CHUNK_DAYS - 1), DATE_END)
        all_datos.extend(_fetch_chunk(cfg, chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(days=1)
        if chunk_start <= DATE_END:
            time.sleep(15)  # evita rate-limit de la API SiAR (~1 req/10s)

    if not all_datos:
        log.error("La respuesta SiAR no contiene registros. Abortando.")
        sys.exit(1)

    log.info("Registros recibidos total: %d", len(all_datos))
    return pd.DataFrame(all_datos)


# ------------------------------------------------------------------ #
# Validación                                                          #
# ------------------------------------------------------------------ #

def validate_station(df: pd.DataFrame, station_id: str) -> pd.DataFrame:
    """Valida, reporta y devuelve el DataFrame de la estación, o aborta."""
    log.info("")
    log.info("** Validación %s (%s) **********************", station_id, STATION_REGION[station_id])

    if df.empty:
        log.error("Sin datos para %s. Abortando.", station_id)
        sys.exit(1)

    df = df.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
    df = df.sort_values("Fecha").reset_index(drop=True)

    n = len(df)
    log.info("  Registros           : %d (esperados %d)", n, EXPECTED_DAYS)
    log.info("  Rango real          : %s → %s", df["Fecha"].iloc[0], df["Fecha"].iloc[-1])

    # Huecos
    all_dates = {DATE_START + timedelta(days=i) for i in range(EXPECTED_DAYS)}
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

def interpolate_gaps(df: pd.DataFrame, station_id: str) -> pd.DataFrame:
    """Inserta filas para días ausentes e interpola linealmente (limit=MAX_INTERP_GAP)."""
    full_range = pd.DataFrame(
        {"Fecha": [DATE_START + timedelta(days=i) for i in range(EXPECTED_DAYS)]}
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
            api.create_task_every(
                name=FLUX_TASK_NAME,
                flux=flux,
                every="1d",
                org=cfg["influx_org"],
            )
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

    # 1. Descarga
    df_all = download_siar(cfg)

    # Columna de estación en la respuesta del SiAR
    station_col = next((c for c in ("Estacion", "Id", "id", "estacion") if c in df_all.columns), None)
    if station_col is None:
        log.error("No se encontró columna de estación en la respuesta SiAR. Columnas: %s", list(df_all.columns))
        sys.exit(1)

    all_daily: list = []
    all_weekly: list = []

    for station_id in STATION_REGION:
        df_st = df_all[df_all[station_col] == station_id].copy()

        # 2. Validar
        df_st = validate_station(df_st, station_id)

        # 3. Interpolar huecos cortos
        df_st = interpolate_gaps(df_st, station_id)

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
