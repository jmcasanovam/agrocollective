"""
Fase 10: Actualización del historial de rendimiento.

Consolida en plot_performance_history una instantánea del estado de cada
parcela al cierre del pipeline nocturno. Un registro por (plot_id, run_date).

Fuentes:
  - Fase 3: PlotAggregates (variables sensoriales, riego, cosecha)
  - Fase 4: ClusteringResult (cluster_id)
  - Fase 5: AnomalyResult (is_anomaly, lof_score)
  - Fase 8: MlPredictionResult (predicted_yield, predicted_efficiency)
  - Fase 9: RecommendationResult (conteo y prioridades)
"""

import logging
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.services.measurements.aggregation_service import PlotAggregates
from app.services.clustering.kmeans_service import ClusteringResult
from app.services.anomalies.lof_service import AnomalyResult
from app.services.ml.prediction_service import MlPredictionResult
from app.services.recommendations.recommendation_service import RecommendationResult

logger = logging.getLogger(__name__)


@dataclass
class PerformanceSnapshot:
    plot_id: UUID
    run_date: date
    cluster_id: int
    avg_soil_humidity: float | None
    avg_air_temp: float | None
    avg_soil_temp: float | None
    avg_air_humidity: float | None
    irrigation_frequency: int | None
    avg_irrigation_mm: float | None
    total_water_mm: float | None
    yield_kg_ha: float | None
    water_efficiency: float | None
    is_anomaly: bool
    lof_score: float | None
    predicted_yield: float | None
    predicted_efficiency: float | None
    n_recommendations: int
    n_high_priority: int


class PerformanceHistoryService:

    def run(
        self,
        aggregates: list[PlotAggregates],
        clustering_result: ClusteringResult,
        anomaly_results: list[AnomalyResult],
        ml_results: list[MlPredictionResult],
        rec_results: list[RecommendationResult],
    ) -> list[PerformanceSnapshot]:
        """
        Genera una instantánea por parcela combinando todos los resultados del pipeline.

        Returns:
            Lista de PerformanceSnapshot, una por parcela.
        """
        run_date = clustering_result.run_date

        # Índices rápidos
        cluster_map: dict[UUID, int] = {
            a.plot_id: a.cluster_id for a in clustering_result.assignments
        }
        anomaly_map: dict[UUID, AnomalyResult] = {r.plot_id: r for r in anomaly_results}
        ml_yield: dict[UUID, float | None] = {}
        ml_eff: dict[UUID, float | None] = {}
        for r in ml_results:
            if r.target == "yield_kg_ha":
                ml_yield[r.plot_id] = r.predicted_value
            elif r.target == "water_efficiency":
                ml_eff[r.plot_id] = r.predicted_value

        rec_count: dict[UUID, int] = {}
        rec_high: dict[UUID, int] = {}
        for r in rec_results:
            rec_count[r.plot_id] = rec_count.get(r.plot_id, 0) + 1
            if r.priority == "high":
                rec_high[r.plot_id] = rec_high.get(r.plot_id, 0) + 1

        snapshots: list[PerformanceSnapshot] = []

        for agg in aggregates:
            pid = agg.plot_id
            anomaly = anomaly_map.get(pid)
            snapshots.append(PerformanceSnapshot(
                plot_id=pid,
                run_date=run_date,
                cluster_id=cluster_map.get(pid, -1),
                avg_soil_humidity=agg.avg_soil_humidity,
                avg_air_temp=agg.avg_air_temp,
                avg_soil_temp=agg.avg_soil_temp,
                avg_air_humidity=agg.avg_air_humidity,
                irrigation_frequency=agg.irrigation_frequency,
                avg_irrigation_mm=agg.avg_irrigation_mm,
                total_water_mm=agg.total_water_mm,
                yield_kg_ha=agg.yield_kg_ha,
                water_efficiency=agg.water_efficiency,
                is_anomaly=anomaly.is_anomaly if anomaly else False,
                lof_score=anomaly.lof_score if anomaly else None,
                predicted_yield=ml_yield.get(pid),
                predicted_efficiency=ml_eff.get(pid),
                n_recommendations=rec_count.get(pid, 0),
                n_high_priority=rec_high.get(pid, 0),
            ))

        logger.info(
            "[Fase 10] %d instantáneas de rendimiento registradas para run_date=%s.",
            len(snapshots), run_date,
        )
        return snapshots


performance_history_service = PerformanceHistoryService()
