"""
Publicador de telemetría en vivo — AgroCollective.

Genera y publica por MQTT una lectura cada 15 minutos para cada dispositivo
activo del sistema (parcelas reales creadas desde la UI y también las
sintéticas del Sprint 2), reutilizando el mismo modelo físico que
`simulate_sensors.py` (curva diurna anclada a SiAR, balance hídrico de
suelo, batería y outliers/anomalías dentro de contexto).

A diferencia de `simulate_sensors.py` (que reproduce una ventana histórica
completa en modo batch), este script está pensado para dejarse corriendo
de forma continua junto al resto de servicios de docker-compose:

  - Anota en InfluxDB, por hash_plot, cuál fue la última lectura publicada.
  - Al arrancar (por ejemplo tras un `docker compose up` después de haber
    estado parado), calcula el hueco entre esa última lectura y el momento
    actual y genera en un buffer todas las lecturas de los 15 minutos que
    faltan por publicar (con un tope de MAX_BACKFILL_HOURS para no inundar
    el sistema si llevaba mucho tiempo parado), y las vuelca a MQTT en orden
    cronológico antes de pasar al modo en vivo.
  - En vivo, cada 15 minutos (alineado a :00/:15/:30/:45 UTC) publica una
    lectura por dispositivo activo.

Uso:
    python scripts/live_sensor_publisher.py [--once] [--dry-run]

Requisitos: los mismos que simulate_sensors.py (paho-mqtt, influxdb-client,
python-dotenv), disponibles ya en la imagen del backend.
"""

import argparse
import os
import sys
import time
import zlib
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPTS_DIR)
sys.path.insert(0, _SCRIPTS_DIR)
sys.path.insert(0, _REPO_ROOT)  # para poder importar el paquete "app" del backend
import simulate_sensors as sim  # noqa: E402  (reutiliza el modelo físico ya validado)

load_dotenv()

# =============================================================================
# CONFIG
# =============================================================================

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

INTERVAL_MINUTES = 15
MAX_BACKFILL_HOURS = 48
BACKFILL_SEND_DELAY = 0.02  # pausa entre mensajes al volcar el buffer de rellenado

# device_code -> perfil de riego usado en simulate_sensors.IRRIG_MM.
# Las parcelas reales creadas desde la UI usan estas etiquetas en español
# (ver plot-form-modal.tsx); las sintéticas del Sprint 2 ya usan las claves
# internas directamente y pasan por este mapa sin cambios.
PROFILE_UI_TO_SIM = {
    "Riego deficitario controlado": "seco_eficiente",
    "Estándar SiAR": "moderado",
    "Riego por goteo optimizado": "humedo_intensivo",
    "Secano": "secano",
}

W = 62


def header(t):
    print(f"\n{'=' * W}\n  {t}\n{'=' * W}", flush=True)


def step(t):
    print(f"\n  --- {t}", flush=True)


def ok(t):
    print(f"  [OK]  {t}", flush=True)


def info(t):
    print(f"  [ ]   {t}", flush=True)


def warn(t):
    print(f"  [!]   {t}", flush=True)


# =============================================================================
# Resolución de dispositivos activos (Postgres)
# =============================================================================


def _normalize_profile(raw_profile: str | None) -> str:
    if not raw_profile:
        return "moderado"
    return PROFILE_UI_TO_SIM.get(raw_profile, raw_profile)


def _nearest_region(farm, regions: list):
    candidates = [r for r in regions if r.latitude is not None and r.longitude is not None]
    if not candidates:
        return None
    if farm.latitude is None or farm.longitude is None:
        return candidates[0]
    return min(
        candidates,
        key=lambda r: (r.latitude - farm.latitude) ** 2 + (r.longitude - farm.longitude) ** 2,
    )


def load_active_devices() -> list[dict]:
    """Devuelve un dict por dispositivo activo con todo lo necesario para simularlo."""
    from app.database.postgres import SessionLocal
    from app.models.device import Device
    from app.models.plot import Plot
    from app.models.farm import Farm
    from app.models.region import Region
    from app.models.soil import Soil

    db = SessionLocal()
    try:
        rows = (
            db.query(Device, Plot, Farm)
            .join(Plot, Plot.id == Device.plot_id)
            .join(Farm, Farm.id == Plot.farm_id)
            .filter(Device.is_active == True)  # noqa: E712
            .all()
        )
        regions = db.query(Region).all()
        regions_by_id = {r.id: r for r in regions}
        soils_by_id = {s.id: s for s in db.query(Soil).all()}
        default_region = regions[0] if regions else None

        devices = []
        for device, plot, farm in rows:
            if not plot.hash_plot:
                continue  # sin hash_plot no se puede anonimizar en InfluxDB (igual que el backend)

            region = regions_by_id.get(farm.region_id) if farm.region_id else None
            region = region or _nearest_region(farm, regions) or default_region
            if region is None or not region.siar_station_code:
                continue  # no hay ninguna estación SiAR de referencia disponible

            soil = soils_by_id.get(plot.soil_id)
            devices.append({
                "code": device.code,
                "hash_plot": plot.hash_plot,
                "station_code": region.siar_station_code,
                "profile": _normalize_profile(plot.management_profile),
                "soil_name": soil.name if soil else "franco",
            })
        return devices
    finally:
        db.close()


def anomaly_plot_index(device_code: str) -> int:
    """
    Índice determinista 0-99 derivado del código real del dispositivo.
    Reutiliza tal cual las anomalías fijas por índice de SensorSimulator
    (1=sesgo temperatura, 3=riego deficitario, 5=sesgo humedad aire,
    7=exceso de riego), de forma que ~4% de los dispositivos reales
    presenten una anomalía persistente y contextual, igual que en el lote
    sintético del Sprint 2.
    """
    return zlib.crc32(device_code.encode("utf-8")) % 100


# =============================================================================
# Clima SiAR — última(s) fecha(s) disponible(s) por estación
# =============================================================================


def load_weather_window(station_codes: set[str], start_date: date, end_date: date) -> dict[str, dict[date, dict]]:
    """Carga el clima diario SiAR solo para el rango [start_date, end_date] necesitado."""
    required = ["INFLUXDB_HOST", "INFLUXDB_PORT", "INFLUXDB_TOKEN", "INFLUXDB_ORG", "INFLUXDB_BUCKET_WEATHER"]
    if any(not os.getenv(k) for k in required) or not station_codes:
        return {}

    url = f"http://{os.environ['INFLUXDB_HOST']}:{os.environ['INFLUXDB_PORT']}"
    token = os.environ["INFLUXDB_TOKEN"]
    org = os.environ["INFLUXDB_ORG"]
    bucket = os.environ["INFLUXDB_BUCKET_WEATHER"]

    range_start = start_date.strftime("%Y-%m-%dT00:00:00Z")
    range_stop = (end_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    fields = (
        "air_temp", "air_temp_max", "air_temp_min",
        "relative_humidity", "relative_humidity_max", "relative_humidity_min",
        "soil_temp", "eto", "precipitation",
    )

    flux = f"""
    from(bucket: "{bucket}")
      |> range(start: {range_start}, stop: {range_stop})
      |> filter(fn: (r) => r._measurement == "weather")
      |> pivot(rowKey: ["_time", "siar_station_code"], columnKey: ["_field"], valueColumn: "_value")
    """
    client = InfluxDBClient(url=url, token=token, org=org)
    weather: dict[str, dict[date, dict]] = {}
    try:
        tables = client.query_api().query(flux, org=org)
        for table in tables:
            for rec in table.records:
                station = rec.values.get("siar_station_code", "")
                if station not in station_codes:
                    continue
                day = rec.get_time().date()
                row = {f: float(rec.values[f]) for f in fields if rec.values.get(f) is not None}
                weather.setdefault(station, {})[day] = row
    finally:
        client.close()
    return weather


def resolve_day_weather(weather: dict[str, dict[date, dict]], station: str, day: date) -> dict:
    """
    Clima del día pedido; si SiAR aún no lo ha publicado (lag habitual),
    recurre al día disponible más reciente de esa estación como proxy.
    """
    station_days = weather.get(station, {})
    if day in station_days:
        return station_days[day]
    if not station_days:
        return {}
    latest = max(station_days)
    return station_days[latest]


# =============================================================================
# Última lectura publicada por hash_plot (para calcular el hueco a rellenar)
# =============================================================================


def load_last_seen_per_hash_plot() -> dict[str, datetime]:
    required = ["INFLUXDB_HOST", "INFLUXDB_PORT", "INFLUXDB_TOKEN", "INFLUXDB_ORG", "INFLUXDB_BUCKET_MEASUREMENTS"]
    if any(not os.getenv(k) for k in required):
        return {}

    url = f"http://{os.environ['INFLUXDB_HOST']}:{os.environ['INFLUXDB_PORT']}"
    token = os.environ["INFLUXDB_TOKEN"]
    org = os.environ["INFLUXDB_ORG"]
    bucket = os.environ["INFLUXDB_BUCKET_MEASUREMENTS"]

    flux = f"""
    from(bucket: "{bucket}")
      |> range(start: -{MAX_BACKFILL_HOURS * 4}h)
      |> filter(fn: (r) => r._measurement == "measurements")
      |> filter(fn: (r) => r._field == "battery")
      |> group(columns: ["hash_plot"])
      |> last()
    """
    client = InfluxDBClient(url=url, token=token, org=org)
    last_seen: dict[str, datetime] = {}
    try:
        tables = client.query_api().query(flux, org=org)
        for table in tables:
            for rec in table.records:
                hash_plot = rec.values.get("hash_plot")
                if hash_plot:
                    last_seen[hash_plot] = rec.get_time()
    finally:
        client.close()
    return last_seen


# =============================================================================
# Generación de lecturas
# =============================================================================


class LiveDevice:
    """Simulador persistente + metadata de un dispositivo activo."""

    def __init__(self, meta: dict):
        self.meta = meta
        self.code = meta["code"]
        self.simulator = sim.SensorSimulator(
            plot_index=anomaly_plot_index(self.code),
            station_code=meta["station_code"],
            profile=meta["profile"],
            soil_type=meta["soil_name"],
        )

    def generate(self, ts: datetime, weather: dict[str, dict[date, dict]]) -> dict:
        day_weather = resolve_day_weather(weather, self.meta["station_code"], ts.date())
        reading = self.simulator.next_reading(ts, day_weather)
        reading["device_id"] = self.code  # el índice interno no es el código real
        reading, _gt = sim.inject_outlier(reading)
        return reading


def align_to_interval(ts: datetime, minutes: int, upward: bool) -> datetime:
    ts = ts.replace(second=0, microsecond=0)
    remainder = ts.minute % minutes
    if remainder == 0:
        return ts
    delta = (minutes - remainder) if upward else -remainder
    return ts + timedelta(minutes=delta)


def publish(reading: dict, dry_run: bool) -> None:
    sim.send_message(reading, dry_run)


# =============================================================================
# MAIN
# =============================================================================


def run_backfill(devices: dict[str, LiveDevice], now: datetime, dry_run: bool) -> None:
    step("Calculando huecos de publicación desde el último arranque")
    last_seen = load_last_seen_per_hash_plot()

    hash_to_code = {d.meta["hash_plot"]: code for code, d in devices.items()}
    stations_needed = {d.meta["station_code"] for d in devices.values()}

    earliest_needed = now
    per_device_ticks: dict[str, list[datetime]] = {}
    for hash_plot, last_ts in last_seen.items():
        code = hash_to_code.get(hash_plot)
        if code is None:
            continue  # dato histórico de un dispositivo ya inactivo/borrado

        gap_start = align_to_interval(last_ts, INTERVAL_MINUTES, upward=True) + timedelta(minutes=INTERVAL_MINUTES)
        max_start = now - timedelta(hours=MAX_BACKFILL_HOURS)
        dropped = 0
        if gap_start < max_start:
            dropped = int((max_start - gap_start).total_seconds() // (INTERVAL_MINUTES * 60))
            gap_start = max_start

        ticks = []
        t = gap_start
        while t <= now:
            ticks.append(t)
            t += timedelta(minutes=INTERVAL_MINUTES)

        if ticks:
            per_device_ticks[code] = ticks
            earliest_needed = min(earliest_needed, ticks[0])
            if dropped:
                warn(f"{code}: llevaba parado más de {MAX_BACKFILL_HOURS}h, se omiten {dropped} lecturas antiguas")

    # Dispositivos sin ninguna lectura previa: una lectura inmediata para que aparezcan ya en el dashboard.
    for code, dev in devices.items():
        if dev.meta["hash_plot"] not in last_seen:
            per_device_ticks.setdefault(code, []).append(now)
            earliest_needed = min(earliest_needed, now)

    if not per_device_ticks:
        ok("No hay huecos que rellenar; todos los dispositivos están al día.")
        return

    weather = load_weather_window(stations_needed, earliest_needed.date(), now.date())

    buffer: list[tuple[datetime, str, dict]] = []
    for code, ticks in per_device_ticks.items():
        for ts in ticks:
            reading = devices[code].generate(ts, weather)
            buffer.append((ts, code, reading))

    buffer.sort(key=lambda item: item[0])
    ok(f"{len(buffer)} lecturas generadas para {len(per_device_ticks)} dispositivos; publicando en orden cronológico...")

    for ts, code, reading in buffer:
        publish(reading, dry_run)
        time.sleep(BACKFILL_SEND_DELAY)

    ok("Buffer de rellenado publicado por completo.")


def run_live_tick(devices: dict[str, LiveDevice], ts: datetime, dry_run: bool) -> None:
    stations_needed = {d.meta["station_code"] for d in devices.values()}
    weather = load_weather_window(stations_needed, ts.date(), ts.date())
    for code, dev in devices.items():
        reading = dev.generate(ts, weather)
        publish(reading, dry_run)


def refresh_devices(current: dict[str, LiveDevice]) -> dict[str, LiveDevice]:
    metas = load_active_devices()
    updated: dict[str, LiveDevice] = {}
    for meta in metas:
        code = meta["code"]
        if code in current:
            current[code].meta = meta  # conserva el estado físico (_sh, _last_day)
            updated[code] = current[code]
        else:
            updated[code] = LiveDevice(meta)
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Publicador de telemetría en vivo AgroCollective")
    parser.add_argument("--dry-run", action="store_true", help="Solo imprime mensajes, no publica ni espera")
    parser.add_argument("--once", action="store_true", help="Ejecuta un único ciclo (rellenado + un tick) y termina")
    args = parser.parse_args()

    header("AgroCollective — Publicador de telemetría en vivo")
    sim.ensure_bucket_exists()

    metas = load_active_devices()
    if not metas:
        warn("No hay dispositivos activos con parcela y región resolubles. Nada que publicar.")
        return

    devices = {meta["code"]: LiveDevice(meta) for meta in metas}
    info(f"Dispositivos activos detectados: {len(devices)}")
    info(f"Cadencia: {INTERVAL_MINUTES} min | Backfill máximo: {MAX_BACKFILL_HOURS} h")
    info(f"MQTT: {MQTT_HOST}:{MQTT_PORT}")

    now = align_to_interval(datetime.now(timezone.utc), INTERVAL_MINUTES, upward=False)
    run_backfill(devices, now, args.dry_run)

    if args.once:
        run_live_tick(devices, now, args.dry_run)
        return

    step("Entrando en modo continuo (una lectura cada 15 minutos)")
    while True:
        next_tick = align_to_interval(datetime.now(timezone.utc), INTERVAL_MINUTES, upward=True)
        sleep_seconds = (next_tick - datetime.now(timezone.utc)).total_seconds()
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

        devices = refresh_devices(devices)
        if devices:
            run_live_tick(devices, next_tick, args.dry_run)
            print(f"  [{next_tick.isoformat()}] {len(devices)} lecturas publicadas", flush=True)


if __name__ == "__main__":
    main()
