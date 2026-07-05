"""
Corrige el problema de "yield_kg_ha" plano/constante por perfil de gestion
(sin relacion real con las condiciones medidas de cada parcela) insertando,
para TODAS las parcelas, una cosecha reciente (mayo-julio 2026) cuyo
rendimiento se deriva del estres hidrico/termico real observado en InfluxDB
en los ultimos 30 dias (misma ventana que usa el pipeline de clustering).

Esto hace que "Rendimiento vs. red" y "Consumo de agua" en el dashboard
dejen de marcar +0.0% para todas las parcelas del mismo perfil, y que el
modelo Random Forest (Fase 8) tenga señal real que aprender.

No borra cosechas antiguas: si ya existe una cosecha en la fecha elegida
para esa parcela, la actualiza; si no, inserta una nueva. La cosecha mas
reciente de cada parcela sigue siendo la que usa aggregation_service.

Uso: docker compose exec backend python scripts/regenerate_recent_harvests.py
"""

import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.postgres import SessionLocal
from app.models.harvest import Harvest
from app.models.plot import Plot
from app.services.measurements.aggregation_service import aggregation_service

SOIL_PARAMS = {
    "arenoso": {"WP": 8, "FC": 40},
    "franco-arenoso": {"WP": 10, "FC": 48},
    "franco": {"WP": 12, "FC": 55},
    "franco-arcilloso": {"WP": 15, "FC": 62},
    "arcilloso": {"WP": 18, "FC": 68},
}
BASE_POTENTIAL = {"vina": 8500.0, "olivo": 4200.0, "almendro": 1600.0}
IRRIG_FALLBACK_MM_WEEK = {"seco_eficiente": 17.5, "moderado": 35.0, "humedo_intensivo": 63.0}

WINDOW_START = date(2026, 5, 1)
WINDOW_END = date(2026, 7, 5)


def stress_factor(avg_soil_humidity, wp, fc):
    if avg_soil_humidity is None:
        norm = 0.5
    else:
        norm = (avg_soil_humidity - wp) / (fc - wp) if fc > wp else 0.5
        norm = max(0.0, min(1.0, norm))
    return max(0.35, 1.0 - abs(norm - 0.6) * 1.3)


def temp_factor(avg_air_temp):
    if avg_air_temp is None:
        return 1.0
    deviation = max(0.0, abs(avg_air_temp - 24.0) - 6.0)
    return max(0.7, 1.0 - deviation * 0.03)


def main():
    db = SessionLocal()
    rng = random.Random(20260705)  # reproducible entre ejecuciones

    plots = db.query(Plot).filter(Plot.hash_plot.isnot(None)).all()
    print(f"Procesando {len(plots)} parcelas...")

    updated, inserted = 0, 0

    for plot in plots:
        crop_name = plot.crop.name
        soil_name = plot.soil.name
        profile = plot.management_profile or "moderado"
        soil = SOIL_PARAMS.get(soil_name, {"WP": 12, "FC": 55})

        agg = aggregation_service.compute(db, plot)

        total_water_mm = agg.total_water_mm
        if not total_water_mm:
            total_water_mm = IRRIG_FALLBACK_MM_WEEK.get(profile, 35.0) * (30 / 7)

        sf = stress_factor(agg.avg_soil_humidity, soil["WP"], soil["FC"])
        tf = temp_factor(agg.avg_air_temp)
        noise = rng.uniform(0.85, 1.18)
        potential = BASE_POTENTIAL.get(crop_name, 4000.0)

        yield_kg_ha = round(potential * sf * tf * noise, 1)
        water_consumed_m3_ha = round(total_water_mm * 10, 1)

        days_span = (WINDOW_END - WINDOW_START).days
        harvest_date = WINDOW_START + timedelta(days=rng.randint(0, days_span))

        current_latest = (
            db.query(Harvest.harvest_date)
            .filter(Harvest.plot_id == plot.id)
            .order_by(Harvest.harvest_date.desc())
            .first()
        )
        if current_latest and current_latest[0] >= harvest_date:
            harvest_date = current_latest[0]  # actualiza la que ya es la mas reciente, en vez de quedar por detras

        existing = (
            db.query(Harvest)
            .filter(Harvest.plot_id == plot.id, Harvest.harvest_date == harvest_date)
            .first()
        )
        if existing:
            existing.yield_kg_ha = yield_kg_ha
            existing.water_consumed_m3_ha = water_consumed_m3_ha
            updated += 1
        else:
            db.add(Harvest(
                plot_id=plot.id,
                harvest_date=harvest_date,
                yield_kg_ha=yield_kg_ha,
                water_consumed_m3_ha=water_consumed_m3_ha,
            ))
            inserted += 1

        db.commit()

    print(f"Listo. {inserted} cosechas nuevas, {updated} actualizadas.")
    db.close()


if __name__ == "__main__":
    main()
