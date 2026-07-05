"""
Fase 9: Generación de recomendaciones agronómicas inteligentes.

Sintetiza los resultados de las fases anteriores para producir recomendaciones
accionables por parcela, clasificadas por categoría y prioridad.

Categorías:
  anomaly:    parcela anómala con causa probable identificada (Fases 5+6)
  prediction: brecha entre valor observado y predicción ML (Fase 8)
  benchmark:  la parcela está por debajo de la media de su cluster (Fase 4)

Prioridad:
  high   → anomalía con causa clara, o brecha de rendimiento > 30 %
  medium → anomalía sin causa clara, o brecha de rendimiento 10-30 %
  low    → diferencia respecto al benchmark < 10 %
"""

import logging
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

# Medida concreta a aplicar segun la feature anomala y el sentido de la
# desviacion ("alto"/"bajo" respecto al resto del cluster). Redactado para un
# productor sin formacion tecnica: que hacer, no solo que se ha detectado.
#
# Solo cubre variables de sensor (lof_service.SENSOR_FEATURE_COLUMNS): riego y
# rendimiento los introduce el propio agricultor a mano, asi que una
# desviacion ahi no es una anomalia de sensor, es una diferencia de manejo:
# esa comparacion ya la hacen las recomendaciones de categoria "benchmark".
_ACTIONS_BY_FEATURE: dict[str, dict[str, str]] = {
    "avg_soil_humidity": {
        "bajo": "Riega antes de lo habitual: el suelo está más seco de lo normal para una parcela como la tuya.",
        "alto": "Reduce o retrasa el próximo riego: el suelo está más húmedo de lo normal, hay riesgo de encharcamiento.",
    },
    "avg_air_temp": {
        "alto": "Vigila el estrés por calor: valora sombreo o un riego de refresco en las horas centrales del día.",
        "bajo": "Vigila el riesgo de frío: protege el cultivo si las temperaturas siguen bajas los próximos días.",
    },
    "avg_soil_temp": {
        "alto": "El suelo está más caliente de lo habitual: si puedes, riega en horas frescas para amortiguarlo.",
        "bajo": "El suelo está más frío de lo habitual: puede ralentizar la absorción de agua y nutrientes.",
    },
    "avg_air_humidity": {
        "alto": "Vigila el riesgo de hongos y plagas: la humedad ambiental es más alta de lo normal.",
        "bajo": "Ambiente más seco de lo normal: vigila el estrés hídrico en las horas de más calor.",
    },
}

_URGENT_LEAD = "Actúa esta semana."
_SOON_LEAD = "No es urgente, pero revísalo en los próximos días."


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
            direction = anomaly.feature_directions.get(feature)
            action = _ACTIONS_BY_FEATURE.get(feature, {}).get(
                direction or "", "Revisa esta parcela: se desvía de lo habitual en tu grupo."
            )
            direction_word = "por encima" if direction == "alto" else "por debajo"

            if causal and causal.causal_feature and causal.explanation:
                cause_label = _FEATURE_LABELS.get(causal.causal_feature, causal.causal_feature)
                title = f"{label.capitalize()} {direction_word} de lo normal, causa probable: {cause_label}"
                body = (
                    f"{_URGENT_LEAD} {action} "
                    f"Motivo probable: {causal.explanation} "
                    f"(relación con {cause_label}: {causal.correlation:+.2f} sobre 1)."
                )
                priority = "high"
            else:
                title = f"{label.capitalize()} {direction_word} de lo normal en esta parcela"
                body = f"{_SOON_LEAD} {action} Revisa también que el sensor esté funcionando bien."
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
            lead = _URGENT_LEAD if priority == "high" else _SOON_LEAD
            title = f"Tu {label} tiene margen de mejora ({pct}% por debajo de lo esperado)"
            body = (
                f"{lead} Parcelas con condiciones de suelo y riego parecidas a la tuya suelen lograr "
                f"un {label} de {predicted:.2f}, y la tuya está en {observed:.2f} ({pct}% menos). "
                f"Revisa la sección \"Parcelas análogas\" de esta parcela para ver con qué manejo "
                f"lo consiguen y qué podrías replicar."
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

        # direction="bajo" dispara cuando observado < media del grupo (mal para
        # eficiencia/humedad); direction="alto" dispara cuando observado > media
        # (mal para volumen de riego: regar de más no es "mejor", es ineficiente).
        checks = [
            (
                agg.water_efficiency,
                cluster_info.cluster_avg_efficiency,
                "eficiencia hídrica",
                "bajo",
                "Produces menos por cada litro de agua que otras parcelas parecidas. Revisa si hay pérdidas de agua (fugas, evaporación, riego fuera de horas frescas) antes de aumentar el riego.",
            ),
            (
                agg.avg_soil_humidity,
                cluster_info.cluster_avg_soil_humidity,
                "humedad del suelo",
                "bajo",
                "El suelo está más seco de lo habitual en tu grupo. Adelanta o intensifica ligeramente el próximo riego.",
            ),
            (
                agg.avg_irrigation_mm,
                cluster_info.cluster_avg_irrigation_mm,
                "volumen de riego",
                "alto",
                "Estás aplicando más agua por riego que otras parcelas parecidas sin que ello se traduzca en más producción. Reduce gradualmente la cantidad por riego y observa si el rendimiento se mantiene.",
            ),
        ]

        for observed, cluster_avg, label, direction, advice in checks:
            if observed is None or cluster_avg is None or cluster_avg == 0:
                continue

            gap = (
                (cluster_avg - observed) / abs(cluster_avg)
                if direction == "bajo"
                else (observed - cluster_avg) / abs(cluster_avg)
            )
            if gap <= _GAP_MEDIUM_THRESHOLD:
                continue

            priority = "high" if gap > _GAP_HIGH_THRESHOLD else "medium"
            pct = round(gap * 100, 1)
            comparativo = "por debajo de" if direction == "bajo" else "por encima de"
            lead = _URGENT_LEAD if priority == "high" else _SOON_LEAD
            title = f"Tu {label} está un {pct}% {comparativo} otras parcelas parecidas"
            body = (
                f"{lead} La media de {label} en parcelas similares a la tuya es {cluster_avg:.2f}, "
                f"la tuya es {observed:.2f} ({pct}% de diferencia). {advice}"
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
