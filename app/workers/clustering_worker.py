"""
Worker de procesamiento inteligente nocturno (Fases 3-10).

Fases implementadas:
  Fase 3  — Obtención de históricos y generación de variables agregadas  ✓
  Fase 4  — Clustering K-Means                                           ✓
  Fase 5  — Detección de anomalías (LOF)                                ✓
  Fase 6  — Análisis causal                                             ✓
  Fase 7  — Búsqueda de parcelas análogas                               ✓
  Fase 8  — Predicción ML (Random Forest)                               ✓
  Fase 8  — Predicción ML                                               (pendiente)
  Fase 9  — Generación de recomendaciones                               (pendiente)
  Fase 10 — Actualización del historial                                 (pendiente)
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.postgres import SessionLocal
from app.models.plot import Plot
from app.services.measurements.aggregation_service import PlotAggregates, aggregation_service
from app.services.clustering.kmeans_service import ClusteringResult, kmeans_service
from app.services.clustering.cluster_statistics import save_clustering_result
from app.services.anomalies.lof_service import AnomalyResult, lof_service
from app.repositories.anomaly_repository import anomaly_repository
from app.services.recommendations.causal_analysis import CausalResult, causal_analysis_service
from app.repositories.causal_repository import causal_repository
from app.services.clustering.analogue_service import AnalogueResult, analogue_service
from app.repositories.analogue_repository import analogue_repository
from app.services.ml.prediction_service import MlPredictionResult, prediction_service
from app.repositories.ml_prediction_repository import ml_prediction_repository

logger = logging.getLogger(__name__)


def run_pipeline(window_days: int | None = None) -> ClusteringResult:
    """
    Ejecuta el pipeline de procesamiento inteligente sobre todas las parcelas activas.

    Args:
        window_days: ventana de días para las variables agregadas.
                     None → usa AGGREGATION_WINDOW_DAYS del .env.

    Returns:
        ClusteringResult con las asignaciones de cluster.
    """
    started_at = datetime.now(timezone.utc)
    logger.info("=== Inicio pipeline clustering | %s ===", started_at.isoformat())

    db: Session = SessionLocal()
    aggregates: list[PlotAggregates] = []

    try:
        # ── Fase 3: variables agregadas ─────────────────────────────────────
        plots: list[Plot] = db.query(Plot).filter(Plot.hash_plot.isnot(None)).all()
        total = len(plots)
        logger.info("[Fase 3] Parcelas a procesar: %d", total)

        for i, plot in enumerate(plots, start=1):
            try:
                agg = aggregation_service.compute(db, plot, window_days)
                aggregates.append(agg)
                logger.info(
                    "[Fase 3][%d/%d] Parcela %s... | hum=%.1f air=%.1f riego=%d total_mm=%s yield=%s eff=%s",
                    i, total, str(plot.id)[:8],
                    agg.avg_soil_humidity or 0,
                    agg.avg_air_temp or 0,
                    agg.irrigation_frequency,
                    f"{agg.total_water_mm:.1f}" if agg.total_water_mm else "—",
                    f"{agg.yield_kg_ha:.1f}" if agg.yield_kg_ha else "—",
                    f"{agg.water_efficiency:.4f}" if agg.water_efficiency else "—",
                )
            except Exception as exc:
                logger.exception("[Fase 3] Error procesando parcela %s: %s", plot.id, exc)

        # ── Fase 4: clustering K-Means ──────────────────────────────────────
        logger.info("[Fase 4] Iniciando K-Means sobre %d parcelas...", len(aggregates))
        clustering_result = kmeans_service.run(aggregates)
        save_clustering_result(db, clustering_result)

        # ── Fase 5: detección de anomalías (LOF) ───────────────────────────
        logger.info("[Fase 5] Iniciando LOF sobre %d parcelas...", len(aggregates))
        anomaly_results: list[AnomalyResult] = lof_service.run(aggregates, clustering_result)
        anomaly_repository.save_results(db, anomaly_results)
        n_anomalies = sum(1 for r in anomaly_results if r.is_anomaly)
        logger.info("[Fase 5] %d anomalías detectadas de %d parcelas.", n_anomalies, len(anomaly_results))

        # ── Fase 6: análisis causal ─────────────────────────────────────────
        logger.info("[Fase 6] Iniciando análisis causal...")
        causal_results: list[CausalResult] = causal_analysis_service.run(
            anomaly_results, db, window_days
        )
        causal_repository.save_results(db, causal_results)
        n_causal = sum(1 for r in causal_results if r.causal_feature)
        logger.info(
            "[Fase 6] %d causas identificadas de %d features anómalas.",
            n_causal, len(causal_results),
        )

        # ── Fase 7: parcelas análogas ───────────────────────────────────────
        logger.info("[Fase 7] Buscando parcelas análogas...")
        analogue_results: list[AnalogueResult] = analogue_service.run(aggregates, clustering_result)
        analogue_repository.save_results(db, analogue_results)
        logger.info("[Fase 7] %d registros de análogas guardados.", len(analogue_results))

        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        logger.info(
            "=== Pipeline completado | Fases 3-8 | %d parcelas | k=%d | %d anomalías | %d causas | %d predicciones | %.1fs ===",
            len(aggregates), clustering_result.n_clusters, n_anomalies, n_causal, n_predicted, elapsed,
        )

        # ── Fase 8: predicción ML ───────────────────────────────────────────
        logger.info("[Fase 8] Iniciando predicción ML (Random Forest)...")
        ml_results: list[MlPredictionResult] = prediction_service.run(aggregates, clustering_result)
        ml_prediction_repository.save_results(db, ml_results)
        n_predicted = sum(1 for r in ml_results if r.predicted_value is not None)
        logger.info("[Fase 8] %d predicciones con valor de %d totales.", n_predicted, len(ml_results))

        # Fases 9-10: se encadenarán aquí

    finally:
        db.close()

    return clustering_result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    days = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_pipeline(window_days=days)
