"""
Añade una finca extra en Valencia (para usar la 6a coordenada aportada para el
TFM) con 2 parcelas, dispositivos, sensores, riego, cosecha y telemetría
InfluxDB coherente con el clima real (SiAR) de la región.

No modifica ni borra nada existente. Idempotente a nivel de farm/plot (falla
con 409 si ya existe una finca/parcela con el mismo nombre, en cuyo caso no
hace falta volver a correrlo).

Uso: docker compose exec backend python scripts/seed_tfm_extra_farm.py
"""

import math
import os
import random
from datetime import datetime, timedelta, timezone

import httpx
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

API_BASE = "http://localhost:8000"
USER_EMAIL = "simulacion2@agrocollective.com"
USER_PASSWORD = "Simul2026!"

FARM = {
    "name": "Finca Valencia 5",
    "latitude": 39.295447,
    "longitude": -0.458921,
    "area_ha": 6.4,
}

PLOTS = [
    {
        "name": "Parcela Viña Sur",
        "crop": "vina",
        "soil": "franco-arenoso",
        "area_ha": 3.2,
        "management_profile": "seco_eficiente",
        "device_code": "AGRO-P100-001",
    },
    {
        "name": "Parcela Olivar Sur",
        "crop": "olivo",
        "soil": "franco",
        "area_ha": 4.1,
        "management_profile": "moderado",
        "device_code": "AGRO-P101-001",
    },
]

SOIL_PARAMS = {
    "arenoso": {"WP": 8, "FC": 40, "dry": 1.4},
    "franco-arenoso": {"WP": 10, "FC": 48, "dry": 1.2},
    "franco": {"WP": 12, "FC": 55, "dry": 1.0},
    "franco-arcilloso": {"WP": 15, "FC": 62, "dry": 0.8},
    "arcilloso": {"WP": 18, "FC": 68, "dry": 0.6},
}
IRRIG_MM = {"seco_eficiente": 2.5, "moderado": 5.0, "humedo_intensivo": 9.0}
MM_TO_PCT = 0.4
HOURS_PER_DAY = [0, 6, 12, 18]
SIM_DAYS = 40  # cubre de sobra la ventana de agregación de 30 dias


def api_login() -> str:
    r = httpx.post(f"{API_BASE}/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD})
    r.raise_for_status()
    return r.json()["access_token"]


def get_catalog(client: httpx.Client) -> dict:
    regions = {r["code"]: r["id"] for r in client.get("/regions").json()}
    crops = {c["name"]: c["id"] for c in client.get("/crops").json()}
    soils = {s["name"]: s["id"] for s in client.get("/soils").json()}
    sensors = [s["id"] for s in client.get("/sensors").json()]
    return {"regions": regions, "crops": crops, "soils": soils, "sensors": sensors}


def daily_weather(influx: InfluxDBClient, region_code: str, start: datetime, end: datetime) -> dict:
    """Devuelve {date: {eto, air_temp, relative_humidity, soil_temp}} desde el bucket SiAR real."""
    query_api = influx.query_api()
    flux = f"""
        from(bucket: "{os.environ['INFLUXDB_BUCKET_WEATHER']}")
          |> range(start: {start.date().isoformat()}T00:00:00Z, stop: {end.date().isoformat()}T00:00:00Z)
          |> filter(fn: (r) => r._measurement == "weather" and r.region_code == "{region_code}")
          |> filter(fn: (r) => r._field == "eto" or r._field == "air_temp" or r._field == "relative_humidity" or r._field == "soil_temp")
    """
    by_day: dict = {}
    for table in query_api.query(flux, org=os.environ["INFLUXDB_ORG"]):
        for rec in table.records:
            day = rec.get_time().date()
            by_day.setdefault(day, {})[rec.get_field()] = rec.get_value()
    return by_day


def generate_points(hash_plot: str, region_code: str, soil: str, profile: str,
                     weather_by_day: dict, start: datetime, end: datetime) -> list:
    params = SOIL_PARAMS[soil]
    irrig_mm_day = IRRIG_MM[profile]
    soil_humidity = params["FC"] * 0.7
    battery_mv = 4150.0

    defaults = {"eto": 4.0, "air_temp": 24.0, "relative_humidity": 55.0, "soil_temp": 22.0}
    sorted_days = sorted(weather_by_day.keys())
    last_known = {**defaults, **weather_by_day[sorted_days[-1]]} if sorted_days else defaults

    points = []
    n_days = (end.date() - start.date()).days
    for day_offset in range(n_days):
        day = start.date() + timedelta(days=day_offset)
        weather = weather_by_day.get(day, last_known)
        eto = weather.get("eto", last_known["eto"]) or 3.0
        base_air_temp = weather.get("air_temp", last_known["air_temp"]) or 23.0
        base_rh = weather.get("relative_humidity", last_known["relative_humidity"]) or 55.0
        base_soil_temp = weather.get("soil_temp", last_known["soil_temp"]) or base_air_temp - 2

        # depleción diaria por evapotranspiración, recarga por riego, ruido pequeño
        soil_humidity -= eto * params["dry"] * 0.5
        soil_humidity += irrig_mm_day * MM_TO_PCT
        soil_humidity = max(params["WP"], min(params["FC"], soil_humidity))
        battery_mv = max(3850.0, battery_mv - random.uniform(2.0, 5.0))

        for hour in HOURS_PER_DAY:
            diurnal = math.sin((hour - 6) / 24 * 2 * math.pi)
            air_temp = round(base_air_temp + diurnal * 5 + random.gauss(0, 0.3), 2)
            soil_temp = round(base_soil_temp + diurnal * 2 + random.gauss(0, 0.2), 2)
            relative_humidity = round(max(20.0, min(95.0, base_rh - diurnal * 12 + random.gauss(0, 1.5))), 2)
            reading_humidity = round(max(params["WP"], min(params["FC"], soil_humidity + random.gauss(0, 0.4))), 2)

            ts = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=hour)
            point = (
                Point("measurements")
                .tag("hash_plot", hash_plot)
                .tag("region_code", region_code)
                .time(ts)
                .field("battery", float(round(battery_mv + random.uniform(-5, 5), 1)))
                .field("soil_humidity", float(reading_humidity))
                .field("air_temp", float(air_temp))
                .field("soil_temp", float(soil_temp))
                .field("relative_humidity", float(relative_humidity))
            )
            points.append(point)
    return points


def main():
    token = api_login()
    client = httpx.Client(base_url=API_BASE, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    catalog = get_catalog(client)

    farm_payload = {**FARM, "region_id": catalog["regions"]["VALENCIA"]}
    r = client.post("/farms", json=farm_payload)
    r.raise_for_status()
    farm = r.json()
    print(f"Finca creada: {farm['name']} ({farm['id']})")

    influx = InfluxDBClient(
        url=f"http://{os.environ['INFLUXDB_HOST']}:{os.environ['INFLUXDB_PORT']}",
        token=os.environ["INFLUXDB_TOKEN"],
        org=os.environ["INFLUXDB_ORG"],
    )
    write_api = influx.write_api(write_options=SYNCHRONOUS)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=SIM_DAYS)
    weather_by_day = daily_weather(influx, "VALENCIA", start, end)
    print(f"Días de clima SiAR real encontrados: {len(weather_by_day)}")

    for plot_def in PLOTS:
        plot_payload = {
            "crop_id": catalog["crops"][plot_def["crop"]],
            "soil_id": catalog["soils"][plot_def["soil"]],
            "name": plot_def["name"],
            "area_ha": plot_def["area_ha"],
            "management_profile": plot_def["management_profile"],
        }
        r = client.post(f"/farms/{farm['id']}/plots", json=plot_payload)
        r.raise_for_status()
        plot = r.json()
        print(f"  Parcela creada: {plot['name']} ({plot['id']}) hash_plot={plot['hash_plot'][:8]}...")

        r = client.post(f"/plots/{plot['id']}/devices", json={"code": plot_def["device_code"]})
        r.raise_for_status()
        device = r.json()
        print(f"    Dispositivo: {device['code']} ({device['id']})")

        r = client.post(
            f"/plots/{plot['id']}/devices/{device['id']}/sensors",
            json={"sensor_ids": catalog["sensors"]},
        )
        r.raise_for_status()

        # Riego semanal (necesario para el analisis causal, min. 4 semanas)
        n_weeks = SIM_DAYS // 7
        week_start = start.date() - timedelta(days=start.date().weekday())
        for w in range(n_weeks):
            wk = week_start + timedelta(weeks=w)
            mm = IRRIG_MM[plot_def["management_profile"]] * 7 * random.uniform(0.8, 1.2)
            resp = client.post(
                f"/plots/{plot['id']}/irrigation",
                json={"week_start": wk.isoformat(), "irrigation_mm": round(mm, 1)},
            )
            if resp.status_code not in (201, 409):
                resp.raise_for_status()

        # Cosecha (para el modelo ML de prediccion de rendimiento)
        yield_by_crop = {"vina": 8500.0, "olivo": 4200.0, "almendro": 1600.0}
        resp = client.post(
            f"/plots/{plot['id']}/harvests",
            json={
                "harvest_date": end.date().isoformat(),
                "yield_kg_ha": yield_by_crop[plot_def["crop"]] * random.uniform(0.9, 1.1),
                "water_consumed_m3_ha": IRRIG_MM[plot_def["management_profile"]] * SIM_DAYS * 10,
            },
        )
        if resp.status_code not in (201, 409):
            resp.raise_for_status()

        points = generate_points(
            plot["hash_plot"], "VALENCIA", plot_def["soil"], plot_def["management_profile"],
            weather_by_day, start, end,
        )
        write_api.write(bucket=os.environ["INFLUXDB_BUCKET_MEASUREMENTS"], record=points)
        print(f"    {len(points)} lecturas InfluxDB escritas")

    influx.close()
    client.close()
    print("Listo.")


if __name__ == "__main__":
    main()
