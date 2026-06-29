"""
Fase 5: Detección de anomalías dentro de cada cluster con Local Outlier Factor (LOF).

Flujo:
  - Por cada cluster de la Fase 4, aplica LOF sobre las parcelas del cluster.
  - Una parcela es anómala si su LOF score supera LOF_THRESHOLD.
  - Para clusters con < 2 miembros no se puede ejecutar LOF (no hay comparación posible).
  - Identifica qué features concretas se desvían más del centro del cluster.

Parámetros .env:
  LOF_N_NEIGHBORS = 5    (se reduce si hay menos miembros en el cluster)
  LOF_THRESHOLD   = 1.5  (scores > umbral → anomalía)
"""

import logging
from dataclasses import dataclass, field
from datetime import date

import numpy as np
from sklearn.neighbors import LocalOutlierFactor

from app.core.config import settings
from app.services.measurements.aggregation_service import PlotAggregates
from app.services.clustering.kmeans_service import ClusteringResult, FEATURE_COLUMNS

logger = logging.getLogger(__name__)

# Desviación estándar mínima respecto al centro del cluster para marcar una feature
_FEATURE_DEVIATION_THRESHOLD = 1.5


@dataclass
class AnomalyResult:
    plot_id: object           # UUID
    hash_plot: str
    cluster_id: int
    run_date: date
    lof_score: float
    is_anomaly: bool
    anomalous_features: list[str] = field(default_factory=list)


class LOFService:

    def run(
        self,
        aggregates: list[PlotAggregates],
        clustering_result: ClusteringResult,
    ) -> list[AnomalyResult]:
        """
        Detecta anomalías en cada cluster usando LOF.

        Args:
            aggregates: variables agregadas por parcela (Fase 3).
            clustering_result: asignaciones de cluster (Fase 4).

        Returns:
            Lista de AnomalyResult, una entrada por parcela procesada.
        """
        if not aggregates or not clustering_result.assignments:
            logger.info("LOF: sin datos para analizar.")
            return []

        # Indexar aggregates por plot_id para acceso rápido
        agg_by_id = {str(a.plot_id): a for a in aggregates}

        # Agrupar asignaciones por cluster
        clusters: dict[int, list] = {}
        for assignment in clustering_result.assignments:
            clusters.setdefault(assignment.cluster_id, []).append(assignment)

        all_results: list[AnomalyResult] = []

        for cluster_id, assignments in clusters.items():
            results = self._analyze_cluster(cluster_id, assignments, agg_by_id, clustering_result.run_date)
            all_results.extend(results)
            n_anomalies = sum(1 for r in results if r.is_anomaly)
            logger.info(
                "[Fase 5] Cluster %d | %d parcelas | %d anomalías detectadas",
                cluster_id, len(assignments), n_anomalies,
            )

        return all_results

    def _analyze_cluster(
        self,
        cluster_id: int,
        assignments: list,
        agg_by_id: dict,
        run_date: date,
    ) -> list[AnomalyResult]:
        """Aplica LOF sobre las parcelas de un cluster."""
        n = len(assignments)

        # Construir matriz de features del cluster
        plot_ids = [str(a.plot_id) for a in assignments]
        hash_plots = [a.hash_plot for a in assignments]
        aggs = [agg_by_id[pid] for pid in plot_ids if pid in agg_by_id]

        if len(aggs) != n:
            logger.warning("Cluster %d: %d parcelas sin agregados — omitidas.", cluster_id, n - len(aggs))
            n = len(aggs)
            plot_ids = [str(a.plot_id) for a in aggs]
            hash_plots = [a.hash_plot for a in aggs]

        X = np.array([[float(getattr(agg, col) or 0) for col in FEATURE_COLUMNS] for agg in aggs])

        if n < 2:
            # Con 1 sola parcela no hay comparación posible — score neutro
            logger.debug("Cluster %d: solo %d parcela, LOF omitido.", cluster_id, n)
            return [
                AnomalyResult(
                    plot_id=aggs[0].plot_id,
                    hash_plot=hash_plots[0],
                    cluster_id=cluster_id,
                    run_date=run_date,
                    lof_score=1.0,
                    is_anomaly=False,
                )
            ]

        # n_neighbors no puede superar n - 1
        n_neighbors = min(settings.LOF_N_NEIGHBORS, n - 1)
        lof = LocalOutlierFactor(n_neighbors=n_neighbors, novelty=False)
        lof.fit_predict(X)

        # negative_outlier_factor_: cuanto más negativo, más anómalo
        # Lo convertimos a positivo: score > LOF_THRESHOLD → anomalía
        scores = -lof.negative_outlier_factor_

        centroid = X.mean(axis=0)
        std = X.std(axis=0)

        results = []
        for i, agg in enumerate(aggs):
            score = float(scores[i])
            is_anomaly = score > settings.LOF_THRESHOLD
            anomalous_features = self._detect_anomalous_features(X[i], centroid, std) if is_anomaly else []

            if is_anomaly:
                logger.info(
                    "  ⚠ Anomalía | Parcela %s... | cluster=%d | lof=%.3f | features=%s",
                    str(agg.plot_id)[:8], cluster_id, score, anomalous_features,
                )

            results.append(AnomalyResult(
                plot_id=agg.plot_id,
                hash_plot=agg.hash_plot,
                cluster_id=cluster_id,
                run_date=run_date,
                lof_score=round(score, 6),
                is_anomaly=is_anomaly,
                anomalous_features=anomalous_features,
            ))

        return results

    @staticmethod
    def _detect_anomalous_features(
        row: np.ndarray, centroid: np.ndarray, std: np.ndarray
    ) -> list[str]:
        """
        Identifica features cuyo valor se desvía más de _FEATURE_DEVIATION_THRESHOLD
        desviaciones estándar respecto al centroide del cluster.
        """
        anomalous = []
        for j, col in enumerate(FEATURE_COLUMNS):
            if std[j] > 0:
                deviation = abs(row[j] - centroid[j]) / std[j]
                if deviation >= _FEATURE_DEVIATION_THRESHOLD:
                    anomalous.append(col)
        return anomalous


lof_service = LOFService()
