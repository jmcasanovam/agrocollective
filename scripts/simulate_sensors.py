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
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

load_dotenv()

# =============================================================================
# CONFIG
# =============================================================================

MQTT_HOST = "localhost"
MQTT_PORT = 1883
N_PLOTS   = 10
DEVICE_PREFIX = "AGRO-P"
SEND_DELAY_SECONDS = 0.02   # pausa entre mensajes en modo FAST

# Ventana de simulación = año móvil del SiAR
START_DATE = date(2025, 7, 1)
END_DATE   = date(2026, 6, 30)

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
    "seco_eficiente",   # P00
    "moderado",         # P01
    "moderado",         # P02
    "seco_eficiente",   # P03
    "humedo_intensivo", # P04
    "moderado",         # P05
    "seco_eficiente",   # P06
    "humedo_intensivo", # P07
    "moderado",         # P08
    "humedo_intensivo", # P09
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
    out = _psql(sql)
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if parts and parts[0]:
            rows.append(parts)
    return rows


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


def load_weather_data() -> dict[str, dict[date, dict]]:
    """
    Devuelve {station_code: {day: {field: float}}} para toda la ventana.
    Usa pivot() para obtener todos los campos de 'weather' en una sola query.
    """
    required = ["INFLUXDB_HOST", "INFLUXDB_PORT", "INFLUXDB_TOKEN",
                "INFLUXDB_ORG", "INFLUXDB_BUCKET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"[ERR] Variables de entorno InfluxDB faltantes: {', '.join(missing)}")
        sys.exit(1)

    url    = f"http://{os.environ['INFLUXDB_HOST']}:{os.environ['INFLUXDB_PORT']}"
    token  = os.environ["INFLUXDB_TOKEN"]
    org    = os.environ["INFLUXDB_ORG"]
    bucket = os.environ["INFLUXDB_BUCKET"]

    flux = f'''
from(bucket: "{bucket}")
  |> range(start: 2025-07-01T00:00:00Z, stop: 2026-07-01T00:00:00Z)
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
    for table in tables:
        for rec in table.records:
            station = rec.values.get("siar_station_code", "")
            if not station:
                continue
            day = rec.get_time().date()
            row = {f: float(rec.values[f]) for f in FIELDS if rec.values.get(f) is not None}
            weather.setdefault(station, {})[day] = row

    summary = ", ".join(f"{k}:{len(v)}d" for k, v in weather.items())
    print(f" {sum(len(v) for v in weather.values())} registros ({summary})")
    return weather


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
        # STOCK: delta modifica el nivel previo; ETo escala por tipo de suelo
        delta  = (precip * 0.8 + irrig * 0.9 - eto * self._dry) * MM_TO_PCT
        # Acotar entre WP y FC del suelo de la parcela (límites físicos)
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
        # Acotada a [WP, FC] del suelo; los outliers se aplican DESPUÉS, fuera del rango
        soil_hum = round(
            max(self._wp, min(self._fc, self._sh + random.gauss(0, 0.4))), 2
        )

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


def main() -> None:
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

    # Resolver device→estación, perfil y tipo de suelo desde BD (con fallback)
    device_station = load_device_station_map()
    device_profile = load_management_profile_map()
    device_soil    = load_soil_type_map()

    # Cargar datos climáticos de InfluxDB
    weather = load_weather_data()

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

    days        = [START_DATE + timedelta(days=d)
                   for d in range((END_DATE - START_DATE).days + 1)]
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
