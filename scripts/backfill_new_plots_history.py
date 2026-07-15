"""
Genera un historico realista de riego (quincenal) y cosechas (2-4 meses,
varios puntos) para las 2 parcelas nuevas de esta sesion (Vina Sur, Olivar
Sur), en vez del unico punto de riego semanal / cosecha que tenian. Los
valores se derivan del clima real SiAR de esa ventana (misma logica de
estres hidrico/termico que regenerate_recent_harvests.py), no de numeros
sueltos. Termina el 2026-07-05 (hoy) y retrocede una duracion aleatoria de
2 a 4 meses por parcela.

Borra y reemplaza SOLO los irrigation_records/harvests de estas 2 parcelas,
no toca las 102 parcelas del dataset original.

Uso: docker compose exec backend python scripts/backfill_new_plots_history.py
"""

import calendar
import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.postgres import SessionLocal
from app.models.harvest import Harvest
from app.models.irrigation_record import IrrigationRecord
from app.database.influx import get_influx_client
from app.core.config import settings

END_DATE = date(2026, 7, 5)

SOIL_PARAMS = {
    "franco-arenoso": {"WP": 10, "FC": 48, "dry": 1.2},
    "franco": {"WP": 12, "FC": 55, "dry": 1.0},
}
BASE_POTENTIAL = {"vina": 8500.0, "olivo": 4200.0}
IRRIG_MM_DAY = {"seco_eficiente": 2.5, "moderado": 5.0}
MM_TO_PCT = 0.4
REFERENCE_ETO = 4.0  # eto "normal" usada como referencia para escalar el riego

PLOTS = [
    {
        "plot_id": "abf76b48-82bd-490d-9b4d-dfa2626dcbf2",
        "crop": "vina",
        "soil": "franco-arenoso",
        "profile": "seco_eficiente",
    },
    {
        "plot_id": "1a489ab4-63b7-4912-aade-2dfde65092df",
        "crop": "olivo",
        "soil": "franco",
        "profile": "moderado",
    },
]


def subtract_months(d: date, months: int) -> date:
    m = d.month - months
    y = d.year
    while m <= 0:
        m += 12
        y -= 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def fetch_weather(region_code: str, start: date, end: date) -> dict:
    client = get_influx_client()
    try:
        query_api = client.query_api()
        flux = f"""
            from(bucket: "{settings.INFLUXDB_BUCKET_WEATHER}")
              |> range(start: {start.isoformat()}T00:00:00Z, stop: {(end + timedelta(days=1)).isoformat()}T00:00:00Z)
              |> filter(fn: (r) => r._measurement == "weather" and r.region_code == "{region_code}")
              |> filter(fn: (r) => r._field == "eto" or r._field == "air_temp")
        """
        by_day: dict = {}
        for table in query_api.query(flux, org=settings.INFLUXDB_ORG):
            for rec in table.records:
                by_day.setdefault(rec.get_time().date(), {})[rec.get_field()] = rec.get_value()
        return by_day
    finally:
        client.close()


def simulate_history(plot_def: dict, start: date, weather_by_day: dict):
    """Devuelve (irrigation_events, daily_humidity) simulando dia a dia."""
    soil = SOIL_PARAMS[plot_def["soil"]]
    irrig_mm_day = IRRIG_MM_DAY[plot_def["profile"]]
    defaults = {"eto": 4.0, "air_temp": 24.0}

    n_days = (END_DATE - start).days + 1
    irrigation_dates = []
    d = END_DATE
    while d >= start:
        irrigation_dates.append(d)
        d -= timedelta(days=14)
    irrigation_dates.sort()
    irrigation_set = set(irrigation_dates)

    humidity = soil["FC"] * 0.7
    daily_humidity: dict[date, float] = {}
    irrigation_events: list[dict] = []

    for offset in range(n_days):
        day = start + timedelta(days=offset)
        weather = weather_by_day.get(day, defaults)
        eto = weather.get("eto") or defaults["eto"]

        humidity -= eto * soil["dry"] * 0.5
        if day in irrigation_set:
            # 14 dias de riego deficitario/moderado concentrados en el evento quincenal,
            # escalado por la ETo media reciente (mas calor/seco -> mas agua).
            recent_eto = [
                (weather_by_day.get(day - timedelta(days=k), defaults).get("eto") or defaults["eto"])
                for k in range(14)
            ]
            eto_avg = sum(recent_eto) / len(recent_eto)
            mm = round(irrig_mm_day * 14 * (eto_avg / REFERENCE_ETO) * random.uniform(0.85, 1.15), 1)
            humidity += mm * MM_TO_PCT
            irrigation_events.append({"date": day, "mm": mm})

        humidity = max(soil["WP"], min(soil["FC"], humidity))
        daily_humidity[day] = humidity

    return irrigation_events, daily_humidity


def compute_yield(plot_def: dict, checkpoint: date, daily_humidity: dict, weather_by_day: dict) -> float:
    soil = SOIL_PARAMS[plot_def["soil"]]
    window = [checkpoint - timedelta(days=k) for k in range(30) if checkpoint - timedelta(days=k) in daily_humidity]
    avg_humidity = sum(daily_humidity[d] for d in window) / len(window) if window else soil["FC"] * 0.6
    temps = [
        weather_by_day.get(d, {}).get("air_temp") for d in window if weather_by_day.get(d, {}).get("air_temp")
    ]
    avg_temp = sum(temps) / len(temps) if temps else 24.0

    norm = (avg_humidity - soil["WP"]) / (soil["FC"] - soil["WP"])
    norm = max(0.0, min(1.0, norm))
    stress = max(0.35, 1.0 - abs(norm - 0.6) * 1.3)
    deviation = max(0.0, abs(avg_temp - 24.0) - 6.0)
    temp_factor = max(0.7, 1.0 - deviation * 0.03)
    noise = random.uniform(0.9, 1.12)

    potential = BASE_POTENTIAL[plot_def["crop"]]
    return round(potential * stress * temp_factor * noise, 1)


def main():
    db = SessionLocal()
    rng_seed = 20260705
    random.seed(rng_seed)

    for plot_def in PLOTS:
        plot_id = plot_def["plot_id"]
        duration_months = random.choice([2, 3, 4])
        start = subtract_months(END_DATE, duration_months)
        print(f"\n{plot_def['crop']} ({plot_id[:8]}...): ventana {start} -> {END_DATE} ({duration_months} meses)")

        weather_by_day = fetch_weather("VALENCIA", start, END_DATE)
        irrigation_events, daily_humidity = simulate_history(plot_def, start, weather_by_day)

        # --- reemplaza irrigation_records de esta parcela ---
        db.query(IrrigationRecord).filter(IrrigationRecord.plot_id == plot_id).delete()
        for event in irrigation_events:
            db.add(IrrigationRecord(plot_id=plot_id, week_start=event["date"], irrigation_mm=event["mm"]))
        db.commit()
        print(f"  Riego quincenal: {len(irrigation_events)} registros ({[e['date'].isoformat() for e in irrigation_events]})")

        # --- reemplaza harvests: un punto por mes dentro de la ventana ---
        db.query(Harvest).filter(Harvest.plot_id == plot_id).delete()
        checkpoints = [subtract_months(END_DATE, duration_months - i - 1) for i in range(duration_months)]
        checkpoints[-1] = END_DATE  # el mas reciente siempre es hoy
        for checkpoint in checkpoints:
            yield_kg_ha = compute_yield(plot_def, checkpoint, daily_humidity, weather_by_day)
            # agua aplicada en los ~30 dias previos a este punto de cosecha
            water_30d = sum(
                e["mm"] for e in irrigation_events if 0 <= (checkpoint - e["date"]).days < 30
            )
            db.add(Harvest(
                plot_id=plot_id,
                harvest_date=checkpoint,
                yield_kg_ha=yield_kg_ha,
                water_consumed_m3_ha=round(water_30d * 10, 1),
            ))
        db.commit()
        print(f"  Cosechas: {[(c.isoformat()) for c in checkpoints]}")

    db.close()
    print("\nListo.")


if __name__ == "__main__":
    main()
