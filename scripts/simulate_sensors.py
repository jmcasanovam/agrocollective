"""
Simulador de sensores IoT anclado al SiAR — AgroCollective (Sprint 2).

Lee datos diarios de InfluxDB measurement 'weather' (precargados por
download_siar.py) y genera telemetría coherente con el clima real de
cada región (BAZA/GR01, VALENCIA/V17).

Uso:
    python scripts/simulate_sensors.py [--dry-run] [--realtime] [--seed N] [--delay S]

Requisitos:
    pip install paho-mqtt influxdb-client python-dotenv
    El broker Mosquitto debe estar accesible (MQTT_HOST/MQTT_PORT).
    Las variables InfluxDB deben estar en .env (mismas que download_siar.py).
"""

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import paho.mqtt.publish as mqtt_publish
import httpx
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

load_dotenv()

# =============================================================================
# CONFIG
# =============================================================================

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
N_PLOTS   = 100
DEVICE_PREFIX = "AGRO-P"
SEND_DELAY_SECONDS = 0.02   # pausa entre mensajes en modo FAST

# Ventana de simulación - determinada dinámicamente desde InfluxDB
START_DATE = None
END_DATE   = None

# 6 h de cadencia → 4 lecturas por dispositivo y día
HOURS_PER_DAY = [0, 6, 12, 18]

# Outliers: tasa configurable, tipo aleatorio, log en JSONL para evaluar LOF
OUTLIER_RATE = 0.02
OUTLIER_LOG  = Path("outliers_ground_truth.jsonl")

# Parámetros físicos por tipo de suelo (FIX2)
# WP = punto de marchitez (%), FC = capacidad de campo (%)
# dry = factor de velocidad de secado (escala el consumo por ETo;
#       arenoso se seca más rápido, arcilloso retiene más)
SOIL_PARAMS: dict[str, dict] = {
    "arenoso":          {"WP":  8, "FC": 40, "dry": 1.4},
    "franco-arenoso":   {"WP": 10, "FC": 48, "dry": 1.2},
    "franco":           {"WP": 12, "FC": 55, "dry": 1.0},
    "franco-arcilloso": {"WP": 15, "FC": 62, "dry": 0.8},
    "arcilloso":        {"WP": 18, "FC": 68, "dry": 0.6},
    "_default":         {"WP": 12, "FC": 55, "dry": 1.0},
}

# Fallback de suelo por índice cuando la BD no responde (cicla los 5 tipos)
_SOIL_NAMES = ["arenoso", "franco-arenoso", "franco", "franco-arcilloso", "arcilloso"]
SOIL_FALLBACK = [_SOIL_NAMES[i % len(_SOIL_NAMES)] for i in range(N_PLOTS)]

# Irrigación diaria añadida (mm) por perfil de gestión
IRRIG_MM   = {"seco_eficiente": 2.5, "moderado": 5.0, "humedo_intensivo": 9.0}
MM_TO_PCT  = 0.4  # mm → % (factor genérico; dry escala el lado de la ETo)

# Fallback de perfil por índice cuando la BD no responde
# (debe coincidir con MANAGEMENT_PROFILES de setup_simulation.py)
PROFILE_FALLBACK = [
    "seco_eficiente" if (i % 3 == 0) else "moderado" if (i % 3 == 1) else "humedo_intensivo"
    for i in range(100)
]

BATTERY_RANGE = (3400, 4100)

# =============================================================================
# Helpers BD (docker exec → psql, mismo patrón que setup_simulation.py)
# =============================================================================


def _psql(sql: str) -> str:
    result = subprocess.run(
        ["docker", "exec", "agro_postgres",
         "psql", "-U", "agro", "-d", "agrocollective",
         "-t", "-A", "-F", "\t", "-c", sql],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _psql_rows(sql: str) -> list[list[str]]:
    try:
        from app.database.postgres import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            result = db.execute(text(sql))
            return [[str(val) for val in row] for row in result.all()]
        finally:
            db.close()
    except Exception:
        out = _psql(sql)
        rows = []
        for line in out.splitlines():
            parts = line.split("\t")
            if parts and parts[0]:
                rows.append(parts)
        return rows


def load_simulation_config_from_api() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """
    Consulta la API REST del backend para construir los mapas device_station,
    device_profile y device_soil dinámicamente sin usar queries SQL directas.
    """
    email = "simulacion@agrocollective.com"
    password = "Simul2026!"
    base_url = "http://localhost:8000"
    
    headers = {}
    print("  Conectando a la API para resolver mapeos de dispositivos...")
    with httpx.Client(timeout=15) as client:
        try:
            r = client.post(f"{base_url}/auth/login", json={"email": email, "password": password})
            if r.status_code != 200:
                print("  [WARN] Login de API fallido. Usando fallbacks de base de datos.")
                return {}, {}, {}
            token = r.json()["access_token"]
            headers["Authorization"] = f"Bearer {token}"
            
            # Obtener catálogo de regiones (para código de estación SiAR)
            r = client.get(f"{base_url}/regions")
            regions = {item["id"]: item["siar_station_code"] for item in r.json() if "siar_station_code" in item}
            
            # Obtener catálogo de suelos (para nombre de suelo)
            r = client.get(f"{base_url}/soils")
            soils = {item["id"]: item["name"] for item in r.json()}
            
            # Obtener fincas
            r = client.get(f"{base_url}/farms", headers=headers)
            farms = r.json()
            
            device_station = {}
            device_profile = {}
            device_soil = {}
            
            for farm in farms:
                farm_id = farm["id"]
                region_id = farm.get("region_id")
                station = regions.get(region_id, "V17")
                
                # Obtener parcelas
                r = client.get(f"{base_url}/farms/{farm_id}/plots", headers=headers)
                plots = r.json()
                for plot in plots:
                    plot_id = plot["id"]
                    profile = plot.get("management_profile", "moderado")
                    soil_id = plot.get("soil_id")
                    soil_name = soils.get(soil_id, "franco")
                    
                    # Obtener dispositivo de la parcela
                    r = client.get(f"{base_url}/plots/{plot_id}/devices", headers=headers)
                    if r.status_code == 200:
                        device = r.json()
                        if device and device.get("is_active"):
                            code = device["code"]
                            device_station[code] = station
                            device_profile[code] = profile
                            device_soil[code] = soil_name
            
            return device_station, device_profile, device_soil
        except Exception as e:
            print(f"  [WARN] Error al consultar API ({type(e).__name__}): {e}. Usando fallbacks de base de datos.")
            return {}, {}, {}


def load_device_station_map() -> dict[str, str]:
    """
    Devuelve {device_code: siar_station_code} leyendo de BD.
    Fallback: V17 para P00-P04, GR01 para P05-P09.
    """
    rows = _psql_rows(
        "SELECT d.code, r.siar_station_code "
        "FROM devices d "
        "JOIN plots p ON d.plot_id = p.id "
        "JOIN farms f ON p.farm_id = f.id "
        "JOIN regions r ON f.region_id = r.id "
        "WHERE d.is_active = true AND r.siar_station_code IS NOT NULL;"
    )
    mapping = {r[0]: r[1] for r in rows if len(r) == 2}
    if not mapping:
        print("[WARN] Sin device→station en BD. Usando fallback (P00-P04=V17, P05-P09=GR01).")
        mapping = {
            f"AGRO-P{i:02d}-001": ("V17" if i < 5 else "GR01")
            for i in range(N_PLOTS)
        }
    return mapping


def load_management_profile_map() -> dict[str, str]:
    """
    Devuelve {device_code: management_profile} leyendo de BD.
    Fallback: PROFILE_FALLBACK por índice.
    """
    rows = _psql_rows(
        "SELECT d.code, p.management_profile "
        "FROM devices d "
        "JOIN plots p ON d.plot_id = p.id "
        "WHERE d.is_active = true AND p.management_profile IS NOT NULL;"
    )
    mapping = {r[0]: r[1] for r in rows if len(r) == 2}
    if not mapping:
        print("[WARN] Sin management_profile en BD. Usando PROFILE_FALLBACK.")
        mapping = {
            f"AGRO-P{i:02d}-001": PROFILE_FALLBACK[i]
            for i in range(N_PLOTS)
        }
    return mapping


def load_soil_type_map() -> dict[str, str]:
    """
    Devuelve {device_code: soil_name} leyendo de BD (Device → Plot → Soil).
    Fallback: cicla los 5 tipos de suelo por índice de parcela.
    """
    rows = _psql_rows(
        "SELECT d.code, s.name "
        "FROM devices d "
        "JOIN plots p ON d.plot_id = p.id "
        "JOIN soils s ON p.soil_id = s.id "
        "WHERE d.is_active = true;"
    )
    mapping = {r[0]: r[1] for r in rows if len(r) == 2}
    if not mapping:
        print("[WARN] Sin soil_type en BD. Usando SOIL_FALLBACK.")
        mapping = {f"AGRO-P{i:02d}-001": SOIL_FALLBACK[i] for i in range(N_PLOTS)}
    return mapping


# =============================================================================
# Carga de datos SiAR desde InfluxDB
# =============================================================================


def load_weather_data() -> tuple[dict[str, dict[date, dict]], date, date]:
    """
    Devuelve (weather, start_date, end_date).
    weather es {station_code: {day: {field: float}}} para toda la ventana.
    Usa pivot() para obtener todos los campos de 'weather' en una sola query.
    Determina start_date y end_date dinámicamente según los timestamps de los registros.
    """
    required = ["INFLUXDB_HOST", "INFLUXDB_PORT", "INFLUXDB_TOKEN",
                "INFLUXDB_ORG", "INFLUXDB_BUCKET_WEATHER"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"[ERR] Variables de entorno InfluxDB faltantes: {', '.join(missing)}")
        sys.exit(1)

    url    = f"http://{os.environ['INFLUXDB_HOST']}:{os.environ['INFLUXDB_PORT']}"
    token  = os.environ["INFLUXDB_TOKEN"]
    org    = os.environ["INFLUXDB_ORG"]
    bucket = os.environ["INFLUXDB_BUCKET_WEATHER"]

    flux = f'''
from(bucket: "{bucket}")
  |> range(start: 2025-06-23T00:00:00Z)
  |> filter(fn: (r) => r._measurement == "weather")
  |> pivot(
       rowKey:    ["_time", "siar_station_code"],
       columnKey: ["_field"],
       valueColumn: "_value"
     )
'''
    print("  Cargando datos SiAR de InfluxDB...", end="", flush=True)
    client = InfluxDBClient(url=url, token=token, org=org)
    try:
        tables = client.query_api().query(flux)
    finally:
        client.close()

    FIELDS = (
        "air_temp", "air_temp_max", "air_temp_min",
        "relative_humidity", "relative_humidity_max", "relative_humidity_min",
        "soil_temp", "eto", "precipitation",
    )

    weather: dict[str, dict[date, dict]] = {}
    all_dates = []
    for table in tables:
        for rec in table.records:
            station = rec.values.get("siar_station_code", "")
            if not station:
                continue
            day = rec.get_time().date()
            all_dates.append(day)
            row = {f: float(rec.values[f]) for f in FIELDS if rec.values.get(f) is not None}
            weather.setdefault(station, {})[day] = row

    if not all_dates:
        print("\n[ERR] No se encontraron datos meteorológicos en InfluxDB. Corre download_siar.py primero.")
        sys.exit(1)

    start_date = min(all_dates)
    end_date = max(all_dates)

    summary = ", ".join(f"{k}:{len(v)}d" for k, v in weather.items())
    print(f" {sum(len(v) for v in weather.values())} registros ({summary})")
    return weather, start_date, end_date


# =============================================================================
# Generación de señales físicas
# =============================================================================


def _diurnal_temp(hour: int, t_min: float, t_max: float) -> float:
    """Coseno: máximo ~15h, mínimo ~3h. cos(0)=1 cuando hour==15."""
    amplitude = (t_max - t_min) / 2
    mid = (t_max + t_min) / 2
    return mid + amplitude * math.cos(2 * math.pi * (hour - 15) / 24)


def _diurnal_humidity(hour: int, h_min: float, h_max: float) -> float:
    """Anti-fase con temperatura: mínimo ~15h, máximo ~3h."""
    amplitude = (h_max - h_min) / 2
    mid = (h_max + h_min) / 2
    return mid - amplitude * math.cos(2 * math.pi * (hour - 15) / 24)


class SensorSimulator:
    """Un dispositivo ESP32 simulado, anclado a los datos SiAR de su estación."""

    def __init__(self, plot_index: int, station_code: str, profile: str, soil_type: str = "_default"):
        self.plot_index   = plot_index
        self.device_code  = f"{DEVICE_PREFIX}{plot_index:02d}-001"
        self.station_code = station_code
        self.profile      = profile
        self.soil_type    = soil_type
        soil = SOIL_PARAMS.get(soil_type, SOIL_PARAMS["_default"])
        self._wp   = soil["WP"]   # punto de marchitez (%)
        self._fc   = soil["FC"]   # capacidad de campo (%)
        self._dry  = soil["dry"]  # factor de secado por ETo
        self._sh   = self._wp + (self._fc - self._wp) * 0.75  # nivel inicial: 75% del agua disponible
        self._last_day: date | None = None

    def _step_water_balance(self, day: date, w: dict) -> None:
        """Balance hídrico diario: llamar una vez por día antes de generar lecturas."""
        if self._last_day == day:
            return
        self._last_day = day
        eto    = w.get("eto", 3.0)
        precip = w.get("precipitation", 0.0)
        irrig  = IRRIG_MM.get(self.profile, 5.0)

        # Inyectar fallos físicos en la simulación de riego (anomalías dinámicas)
        if self.plot_index == 3:
            # Parcela 3: Riego deficitario severo (20% del riego normal). Se seca dinámicamente con ETo.
            irrig = 0.2 * IRRIG_MM.get(self.profile, 5.0)
        elif self.plot_index == 7:
            # Parcela 7: Exceso de riego continuo (doble del riego normal).
            irrig = 2.0 * IRRIG_MM.get(self.profile, 5.0)

        # STOCK: delta modifica el nivel previo; ETo escala por tipo de suelo
        delta  = (precip * 0.8 + irrig * 0.9 - eto * self._dry) * MM_TO_PCT
        
        # Ajustar límites físicos de acumulación de agua según el tipo de anomalía
        if self.plot_index == 3:
            # Límite inferior ligeramente expandido por debajo del punto de marchitez
            self._sh = max(self._wp - 1.5, min(self._fc, self._sh + delta))
        elif self.plot_index == 7:
            # Límite superior ligeramente expandido por encima de la capacidad de campo
            self._sh = max(self._wp, min(self._fc + 3.0, self._sh + delta))
        else:
            self._sh = max(self._wp, min(self._fc, self._sh + delta))

    def next_reading(self, ts: datetime, day_weather: dict) -> dict:
        day = ts.date()
        self._step_water_balance(day, day_weather)
        hour = ts.hour

        # Temperatura del aire — curva sinusoidal anclada a max/min del día
        t_mean = day_weather.get("air_temp", 20.0)
        t_max  = day_weather.get("air_temp_max",  t_mean + 5.0)
        t_min  = day_weather.get("air_temp_min",  t_mean - 5.0)
        air_temp = round(
            _diurnal_temp(hour, t_min, t_max) + random.gauss(0, 0.3), 2
        )

        # Humedad del aire — anti-fase, anclada a max/min del día
        h_mean = day_weather.get("relative_humidity", 60.0)
        h_max  = day_weather.get("relative_humidity_max", min(100.0, h_mean + 10.0))
        h_min  = day_weather.get("relative_humidity_min", max(10.0,  h_mean - 10.0))
        air_hum = round(
            max(10.0, min(100.0,
                _diurnal_humidity(hour, h_min, h_max) + random.gauss(0, 0.5))),
            2,
        )

        # Temperatura del suelo — media diaria SiAR + oscilación retardada ~3h respecto al aire
        # cos(hour-18): pico ~18h (3h después del pico del aire a las 15h)
        s_mean    = day_weather.get("soil_temp", t_mean - 2.0)
        soil_temp = round(
            s_mean
            + 1.5 * math.cos(2 * math.pi * (hour - 18) / 24)
            + random.gauss(0, 0.2),
            2,
        )

        # Humedad del suelo — oscilación intra-día sobre el nivel diario (STOCK)
        # Acotada al rango físico ajustado de la parcela
        wp_limit = self._wp - 1.5 if self.plot_index == 3 else self._wp
        fc_limit = self._fc + 3.0 if self.plot_index == 7 else self._fc
        soil_hum = round(
            max(wp_limit, min(fc_limit, self._sh + random.gauss(0, 0.4))), 2
        )

        # Inyectar anomalías de sensor/microclima para cubrir todas las variables medidas
        if self.plot_index == 1:
            # Parcela 1: Anomalía de temperatura (ej. calor local / mala ubicación del sensor)
            air_temp = round(air_temp + 4.5, 2)
            soil_temp = round(soil_temp + 3.5, 2)
        elif self.plot_index == 5:
            # Parcela 5: Anomalía de humedad del aire (ej. sensor descalibrado, lectura baja)
            air_hum = round(max(10.0, air_hum - 20.0), 2)

        battery = int(random.uniform(*BATTERY_RANGE))

        return {
            "device_id":  self.device_code,
            "timestamp":  ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "battery_mv": battery,
            "measures": {
                "soil_humidity": soil_hum,
                "air_temp":      air_temp,
                "soil_temp":     soil_temp,
                "air_humidity":  air_hum,
            },
        }


# =============================================================================
# Inyección de outliers etiquetados
# =============================================================================

_OUTLIER_TYPES = ("spike_high", "spike_low", "zero", "disconnect")


def inject_outlier(
    payload: dict,
) -> tuple[dict, dict | None]:
    """
    Con probabilidad OUTLIER_RATE sustituye un campo por un valor anómalo.
    Devuelve (payload modificado, registro ground-truth | None).
    """
    if random.random() >= OUTLIER_RATE:
        return payload, None

    kind  = random.choice(_OUTLIER_TYPES)
    field = random.choice(list(payload["measures"].keys()))
    clean = payload["measures"][field]

    if kind == "spike_high":
        dirty = round(clean * random.uniform(1.8, 3.0), 2)
    elif kind == "spike_low":
        dirty = round(clean * random.uniform(0.05, 0.3), 2)
    elif kind == "zero":
        dirty = 0.0
    else:  # disconnect
        dirty = -127.0

    modified = {**payload, "measures": {**payload["measures"], field: dirty}}
    gt = {
        "device_id": payload["device_id"],
        "timestamp": payload["timestamp"],
        "field":     field,
        "type":      kind,
        "clean":     clean,
        "dirty":     dirty,
    }
    return modified, gt


# =============================================================================
# Envío MQTT
# =============================================================================


def send_message(payload: dict, dry_run: bool) -> None:
    topic = f"devices/{payload['device_id']}/readings"
    body  = json.dumps(payload)
    if dry_run:
        print(f"  [DRY-RUN] {topic} → {body}")
        return
    try:
        mqtt_publish.single(topic, body, hostname=MQTT_HOST, port=MQTT_PORT)
    except Exception as exc:
        print(f"  [ERROR] {topic}: {exc}")


# =============================================================================
# MAIN
# =============================================================================


def ensure_bucket_exists() -> None:
    """Asegura que el bucket de mediciones de InfluxDB exista."""
    required = ["INFLUXDB_HOST", "INFLUXDB_PORT", "INFLUXDB_TOKEN",
                "INFLUXDB_ORG", "INFLUXDB_BUCKET_MEASUREMENTS"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        return

    url    = f"http://{os.environ['INFLUXDB_HOST']}:{os.environ['INFLUXDB_PORT']}"
    token  = os.environ["INFLUXDB_TOKEN"]
    org    = os.environ["INFLUXDB_ORG"]
    bucket = os.environ["INFLUXDB_BUCKET_MEASUREMENTS"]

    client = InfluxDBClient(url=url, token=token, org=org)
    try:
        buckets_api = client.buckets_api()
        existing = buckets_api.find_bucket_by_name(bucket)
        if not existing:
            orgs_api = client.organizations_api()
            orgs = orgs_api.find_organizations(org=org)
            if orgs:
                buckets_api.create_bucket(bucket_name=bucket, org_id=orgs[0].id)
                print(f"  [INFO] Creado bucket de InfluxDB '{bucket}'.")
    except Exception as exc:
        print(f"  [WARN] No se pudo verificar/crear el bucket '{bucket}': {exc}")
    finally:
        client.close()


def main() -> None:
    ensure_bucket_exists()
    parser = argparse.ArgumentParser(
        description="Simulador de sensores AgroCollective (Sprint 2 — SiAR-anclado)"
    )
    parser.add_argument("--realtime", action="store_true",
                        help="Espera 6 h reales entre ciclos (modo continuo)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo imprime mensajes, no envía")
    parser.add_argument("--seed", type=int, default=42,
                        help="Semilla aleatoria (default: 42)")
    parser.add_argument("--delay", type=float, default=SEND_DELAY_SECONDS,
                        help=f"Pausa entre mensajes en modo FAST (default: {SEND_DELAY_SECONDS}s)")
    args = parser.parse_args()
    random.seed(args.seed)

    print("\n=== AgroCollective — Simulador SiAR-anclado (Sprint 2) ===")

    # Resolver device→estación, perfil y tipo de suelo desde API (con fallback a SQL)
    device_station, device_profile, device_soil = load_simulation_config_from_api()
    if not device_station:
        device_station = load_device_station_map()
        device_profile = load_management_profile_map()
        device_soil    = load_soil_type_map()

    # Cargar datos climáticos de InfluxDB
    weather, START_DATE, END_DATE = load_weather_data()

    # Construir simuladores
    simulators = []
    for i in range(N_PLOTS):
        code    = f"{DEVICE_PREFIX}{i:02d}-001"
        station = device_station.get(code, "V17" if i < 5 else "GR01")
        profile = device_profile.get(code, PROFILE_FALLBACK[i])
        soil    = device_soil.get(code, SOIL_FALLBACK[i])
        sp      = SOIL_PARAMS.get(soil, SOIL_PARAMS["_default"])
        simulators.append(SensorSimulator(i, station, profile, soil))
        print(f"  {code}  estacion={station}  perfil={profile}  "
              f"suelo={soil}  WP={sp['WP']}%  FC={sp['FC']}%")

    all_days    = [START_DATE + timedelta(days=d)
                   for d in range((END_DATE - START_DATE).days + 1)]
    days        = all_days[-45:]
    total_msgs  = len(days) * len(HOURS_PER_DAY) * N_PLOTS

    print(f"\n  Ventana:     {START_DATE} → {END_DATE}  ({len(days)} días)")
    print(f"  Cadencia:    6 h  →  {len(HOURS_PER_DAY)} lecturas/día/dispositivo")
    print(f"  Total msgs:  {total_msgs}")
    print(f"  Outlier rate: {OUTLIER_RATE:.0%}")
    print(f"  Modo:        {'REALTIME' if args.realtime else 'FAST'} | "
          f"{'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"  MQTT:        {MQTT_HOST}:{MQTT_PORT}")
    print()

    outlier_log = open(OUTLIER_LOG, "w") if not args.dry_run else None
    sent = outliers = 0

    try:
        for day in days:
            print(f"[{day}] {len(HOURS_PER_DAY) * N_PLOTS} msgs...", end="\r")
            for hour in HOURS_PER_DAY:
                ts = datetime(day.year, day.month, day.day, hour, 0, 0,
                              tzinfo=timezone.utc)
                for sim in simulators:
                    day_weather = weather.get(sim.station_code, {}).get(day, {})
                    reading = sim.next_reading(ts, day_weather)
                    reading, gt = inject_outlier(reading)
                    if gt and outlier_log:
                        outlier_log.write(json.dumps(gt) + "\n")
                        outliers += 1
                    send_message(reading, args.dry_run)
                    sent += 1
                    if not args.realtime:
                        time.sleep(args.delay)

                if args.realtime:
                    print(f"\n  → Esperando 6 h hasta el próximo ciclo...")
                    time.sleep(6 * 3600)
    finally:
        if outlier_log:
            outlier_log.close()

    print(f"\n=== Completado: {sent} msgs enviados, {outliers} outliers inyectados ===")
    if not args.dry_run and outliers:
        print(f"  Ground-truth: {OUTLIER_LOG}  ({outliers} registros)")


if __name__ == "__main__":
    main()
