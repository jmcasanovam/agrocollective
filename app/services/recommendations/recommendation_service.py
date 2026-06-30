"""
Fase 9: Generación de recomendaciones agronómicas inteligentes.

Sintetiza los resultados de las fases anteriores para producir recomendaciones
accionables por parcela, clasificadas por categoría y prioridad.

Categorías:
  anomaly    — parcela anómala con causa probable identificada (Fases 5+6)
  prediction — brecha entre valor observado y predicción ML (Fase 8)
  benchmark  — la parcela está por debajo de la media de su cluster (Fase 4)

Prioridad:
  high   → anomalía con causa clara, o brecha de rendimiento > 30 %
  medium → anomalía sin causa clara, o brecha de rendimiento 10-30 %
  low    → diferencia respecto al benchmark < 10 %
"""

import logging
import math
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.services.anomalies.lof_service import AnomalyResult
from app.services.recommendations.causal_analysis import CausalResult
from app.services.ml.prediction_service import MlPredictionResult
from app.services.clustering.kmeans_service import ClusteringResult, PlotClusterResult
from app.services.measurements.aggregation_service import PlotAggregates

logger = logging.getLogger(__name__)

_GAP_HIGH_THRESHOLD = 0.30
_GAP_MEDIUM_THRESHOLD = 0.10

_FEATURE_LABELS: dict[str, str] = {
    "avg_soil_humidity":    "humedad del suelo",
    "avg_air_temp":         "temperatura del aire",
    "avg_soil_temp":        "temperatura del suelo",
    "avg_air_humidity":     "humedad del aire",
    "relative_humidity":    "humedad relativa",
    "soil_humidity":        "humedad del suelo",
    "air_temp":             "temperatura del aire",
    "soil_temp":            "temperatura del suelo",
    "irrigation_frequency": "frecuencia de riego",
    "avg_irrigation_mm":    "volumen medio de riego",
    "total_water_mm":       "agua total aplicada",
    "yield_kg_ha":          "rendimiento (kg/ha)",
    "water_efficiency":     "eficiencia hídrica",
    "irrigation_mm":        "volumen de riego",
}


@dataclass
class RecommendationResult:
    plot_id: UUID
    run_date: date
    category: str   # anomaly | prediction | benchmark
    priority: str   # high | medium | low
    title: str
    body: str


class RecommendationService:

    def run(
        self,
        aggregates: list[PlotAggregates],
        clustering_result: ClusteringResult,
        anomaly_results: list[AnomalyResult],
        causal_results: list[CausalResult],
        ml_results: list[MlPredictionResult],
    ) -> list[RecommendationResult]:
        """
        Genera recomendaciones para todas las parcelas del pipeline.

        Returns:
            Lista de RecommendationResult (0-N por parcela según hallazgos).
        """
        agg_map: dict[UUID, PlotAggregates] = {a.plot_id: a for a in aggregates}
        cluster_map: dict[UUID, PlotClusterResult] = {
            a.plot_id: a for a in clustering_result.assignments
        }
        anomaly_map: dict[UUID, AnomalyResult] = {r.plot_id: r for r in anomaly_results}
        causal_by_plot: dict[UUID, list[CausalResult]] = {}
        for r in causal_results:
            causal_by_plot.setdefault(r.plot_id, []).append(r)
        ml_by_plot: dict[UUID, dict[str, MlPredictionResult]] = {}
        for r in ml_results:
            ml_by_plot.setdefault(r.plot_id, {})[r.target] = r

        all_recs: list[RecommendationResult] = []
        run_date = clustering_result.run_date

        for agg in aggregates:
            pid = agg.plot_id
            cluster_info = cluster_map.get(pid)

            anomaly = anomaly_map.get(pid)
            if anomaly and anomaly.is_anomaly:
                all_recs.extend(
                    self._anomaly_recommendations(pid, run_date, anomaly, causal_by_plot.get(pid, []))
                )

            if pid in ml_by_plot:
                all_recs.extend(
                    self._prediction_recommendations(pid, run_date, agg, ml_by_plot[pid])
                )

            if cluster_info:
                all_recs.extend(
                    self._benchmark_recommendations(pid, run_date, agg, cluster_info)
                )

        logger.info(
            "[Fase 9] %d recomendaciones generadas para %d parcelas.",
            len(all_recs), len(aggregates),
        )
        return all_recs

    # -------------------------------------------------------------------------
    # Categoría: anomaly
    # -------------------------------------------------------------------------

    def _anomaly_recommendations(
        self,
        plot_id: UUID,
        run_date: date,
        anomaly: AnomalyResult,
        causal_results: list[CausalResult],
    ) -> list[RecommendationResult]:
        recs = []
        causal_map: dict[str, CausalResult] = {r.anomalous_feature: r for r in causal_results}

        for feature in anomaly.anomalous_features:
            label = _FEATURE_LABELS.get(feature, feature)
            causal = causal_map.get(feature)

            if causal and causal.causal_feature and causal.explanation:
                cause_label = _FEATURE_LABELS.get(causal.causal_feature, causal.causal_feature)
                title = f"Anomalía en {label}: posible {cause_label} inadecuado/a"
                body = (
                    f"Tu parcela presenta un valor anómalo de {label} "
                    f"(LOF score: {anomaly.lof_score:.2f}). "
                    f"{causal.explanation} "
                    f"Correlación estadística: {causal.correlation:+.2f}. "
                    f"Revisa los registros de {cause_label} de las últimas semanas."
                )
                priority = "high"
            else:
                title = f"Anomalía detectada en {label}"
                body = (
                    f"Tu parcela presenta un valor estadísticamente inusual de {label} "
                    f"respecto al resto de parcelas de su grupo "
                    f"(LOF score: {anomaly.lof_score:.2f}). "
                    f"No se ha podido determinar la causa automáticamente. "
                    f"Se recomienda revisar el estado del sensor y los registros de campo."
                )
                priority = "medium"

            recs.append(RecommendationResult(
                plot_id=plot_id,
                run_date=run_date,
                category="anomaly",
                priority=priority,
                title=title,
                body=body,
            ))

        return recs

    # -------------------------------------------------------------------------
    # Categoría: prediction
    # -------------------------------------------------------------------------

    def _prediction_recommendations(
        self,
        plot_id: UUID,
        run_date: date,
        agg: PlotAggregates,
        ml_map: dict[str, MlPredictionResult],
    ) -> list[RecommendationResult]:
        recs = []

        targets = [
            ("yield_kg_ha",      agg.yield_kg_ha,      "rendimiento (kg/ha)"),
            ("water_efficiency",  agg.water_efficiency,  "eficiencia hídrica"),
        ]

        for target_key, observed, label in targets:
            pred = ml_map.get(target_key)
            if not pred or pred.predicted_value is None or observed is None:
                continue

            predicted = pred.predicted_value
            if predicted == 0:
                continue

            gap = (predicted - observed) / abs(predicted)

            if gap > _GAP_HIGH_THRESHOLD:
                priority = "high"
            elif gap > _GAP_MEDIUM_THRESHOLD:
                priority = "medium"
            else:
                continue

            pct = round(gap * 100, 1)
            r2 = pred.model_r2
            r2_str = f"{r2:.2f}" if r2 is not None and not math.isnan(r2) else "N/A"
            title = f"Tu {label} está un {pct}% por debajo del potencial estimado"
            body = (
                f"El modelo de predicción estima que parcelas con tus condiciones "
                f"alcanzan un {label} de {predicted:.2f}, pero tu valor actual es {observed:.2f} "
                f"({pct}% de diferencia). "
                f"Compara tus prácticas con las parcelas análogas de tu grupo "
                f"para identificar oportunidades de mejora. "
                f"(R² del modelo: {r2_str}, entrenado con {pred.n_training_samples} parcelas)"
            )

            recs.append(RecommendationResult(
                plot_id=plot_id,
                run_date=run_date,
                category="prediction",
                priority=priority,
                title=title,
                body=body,
            ))

        return recs

    # -------------------------------------------------------------------------
    # Categoría: benchmark
    # -------------------------------------------------------------------------

    def _benchmark_recommendations(
        self,
        plot_id: UUID,
        run_date: date,
        agg: PlotAggregates,
        cluster_info: PlotClusterResult,
    ) -> list[RecommendationResult]:
        recs = []

        checks = [
            (
                agg.water_efficiency,
                cluster_info.cluster_avg_efficiency,
                "eficiencia hídrica",
                "Optimiza el calendario y volumen de riego para reducir el agua aplicada por kg de cosecha.",
            ),
            (
                agg.avg_soil_humidity,
                cluster_info.cluster_avg_soil_humidity,
                "humedad del suelo",
                "Revisa la programación de riegos para acercarte a los valores medios de tu grupo.",
            ),
            (
                agg.avg_irrigation_mm,
                cluster_info.cluster_avg_irrigation_mm,
                "volumen de riego",
                "Tu volumen de riego supera la media del grupo. Considera reducirlo para mejorar la eficiencia.",
            ),
        ]

        for observed, cluster_avg, label, advice in checks:
            if observed is None or cluster_avg is None or cluster_avg == 0:
                continue

            gap = (cluster_avg - observed) / abs(cluster_avg)
            if gap <= _GAP_MEDIUM_THRESHOLD:
                continue

            priority = "high" if gap > _GAP_HIGH_THRESHOLD else "medium"
            pct = round(gap * 100, 1)
            title = f"Tu {label} está un {pct}% por debajo de la media de tu grupo"
            body = (
                f"La media de {label} en tu cluster es {cluster_avg:.2f}, "
                f"mientras que tu valor es {observed:.2f} ({pct}% de diferencia). "
                f"{advice}"
            )

            recs.append(RecommendationResult(
                plot_id=plot_id,
                run_date=run_date,
                category="benchmark",
                priority=priority,
                title=title,
                body=body,
            ))

        return recs


recommendation_service = RecommendationService()
