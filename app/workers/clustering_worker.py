"""
Worker de procesamiento inteligente nocturno (Fases 3-10).

Ejecuta el pipeline completo sobre todas las parcelas activas:
  Fase 3  — Obtención de históricos y generación de variables agregadas
  Fase 4  — Clustering K-Means                   (pendiente)
  Fase 5  — Detección de anomalías (LOF)          (pendiente)
  Fase 6  — Análisis causal                       (pendiente)
  Fase 7  — Búsqueda de parcelas análogas         (pendiente)
  Fase 8  — Predicción ML                         (pendiente)
  Fase 9  — Generación de recomendaciones         (pendiente)
  Fase 10 — Actualización del historial           (pendiente)

Puede lanzarse manualmente o programarse via APScheduler / cron.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.postgres import SessionLocal
from app.models.plot import Plot
from app.services.measurements.aggregation_service import PlotAggregates, aggregation_service

logger = logging.getLogger(__name__)


def run_pipeline(window_days: int | None = None) -> list[PlotAggregates]:
    """
    Ejecuta el pipeline de procesamiento inteligente sobre todas las parcelas activas.

    Args:
        window_days: ventana de días para las variables agregadas.
                     None → usa AGGREGATION_WINDOW_DAYS del .env.

    Returns:
        Lista de PlotAggregates con las variables calculadas de cada parcela.
    """
    started_at = datetime.now(timezone.utc)
    logger.info("=== Inicio pipeline clustering | %s ===", started_at.isoformat())

    db: Session = SessionLocal()
    results: list[PlotAggregates] = []

    try:
        plots: list[Plot] = db.query(Plot).filter(Plot.hash_plot.isnot(None)).all()
        total = len(plots)
        logger.info("Parcelas a procesar: %d", total)

        for i, plot in enumerate(plots, start=1):
            try:
                agg = aggregation_service.compute(db, plot, window_days)
                results.append(agg)
                logger.info(
                    "[%d/%d] Parcela %s... | hum=%.1f air=%.1f riego=%d total_mm=%s yield=%s eff=%s",
                    i, total,
                    str(plot.id)[:8],
                    agg.avg_soil_humidity or 0,
                    agg.avg_air_temp or 0,
                    agg.irrigation_frequency,
                    f"{agg.total_water_mm:.1f}" if agg.total_water_mm else "—",
                    f"{agg.yield_kg_ha:.1f}" if agg.yield_kg_ha else "—",
                    f"{agg.water_efficiency:.4f}" if agg.water_efficiency else "—",
                )
            except Exception as exc:
                logger.exception("Error procesando parcela %s: %s", plot.id, exc)

        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        logger.info("=== Fase 3 completada | %d/%d parcelas | %.1fs ===", len(results), total, elapsed)

        # Fases 4-10: se añadirán aquí de forma encadenada
        # results = kmeans_service.run(results)
        # anomalies = lof_service.run(results)
        # ...

    finally:
        db.close()

    return results


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    days = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_pipeline(window_days=days)
