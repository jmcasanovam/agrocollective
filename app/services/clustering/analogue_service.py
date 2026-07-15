"""
Fase 7: Búsqueda de parcelas análogas.

Para cada parcela, encuentra las ANALOGUE_TOP_N parcelas más parecidas
(distancia euclidiana en el espacio de features normalizado).

Estrategia:
  1. Reconstruir la matriz normalizada con el mismo StandardScaler que Fase 4.
  2. Calcular la matriz de distancias pairwise (N×N).
  3. Para cada parcela, ordenar las demás por distancia ascendente y tomar las top-N.
  4. Marcar si la análoga pertenece al mismo cluster (same_cluster).

Parámetros .env:
  ANALOGUE_TOP_N = 5   (número de análogas a guardar por parcela)
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import UUID

import numpy as np
from sklearn.preprocessing import StandardScaler

from app.core.config import settings
from app.services.measurements.aggregation_service import PlotAggregates
from app.services.clustering.kmeans_service import (
    ClusteringResult,
    FEATURE_COLUMNS,
)

logger = logging.getLogger(__name__)


@dataclass
class AnalogueResult:
    plot_id: UUID
    analogue_plot_id: UUID
    run_date: date
    rank: int
    distance: float
    same_cluster: bool


class AnalogueService:

    def run(
        self,
        aggregates: list[PlotAggregates],
        clustering_result: ClusteringResult,
    ) -> list[AnalogueResult]:
        """
        Calcula las parcelas más análogas para cada parcela del pipeline.

        Args:
            aggregates: variables agregadas de todas las parcelas (Fase 3).
            clustering_result: resultado de K-Means (Fase 4), para saber el cluster.

        Returns:
            Lista de AnalogueResult; vacía si hay menos de 2 parcelas.
        """
        n = len(aggregates)
        if n < 2:
            logger.info("[Fase 7] Menos de 2 parcelas, sin análogas que calcular.")
            return []

        run_date = clustering_result.run_date
        top_n = min(settings.ANALOGUE_TOP_N, n - 1)

        # Matriz de features (None → 0) y normalización
        X_raw = np.array(
            [[float(getattr(agg, col) or 0) for col in FEATURE_COLUMNS] for agg in aggregates],
            dtype=float,
        )
        X_scaled = StandardScaler().fit_transform(X_raw)

        # Mapa plot_id → cluster_id
        cluster_map: dict[UUID, int] = {
            a.plot_id: a.cluster_id for a in clustering_result.assignments
        }

        # Matriz de distancias pairwise (N×N)
        diff = X_scaled[:, np.newaxis, :] - X_scaled[np.newaxis, :, :]
        dist_matrix = np.sqrt((diff ** 2).sum(axis=2))   # shape (N, N)

        results: list[AnalogueResult] = []

        for i, agg in enumerate(aggregates):
            # Distancias a las demás parcelas, ordenadas ascendentemente (excluir i mismo)
            dists = dist_matrix[i].copy()
            dists[i] = np.inf
            nearest_indices = np.argsort(dists)[:top_n]

            for rank, j in enumerate(nearest_indices, start=1):
                analogue = aggregates[j]
                same = cluster_map.get(agg.plot_id) == cluster_map.get(analogue.plot_id)
                results.append(AnalogueResult(
                    plot_id=agg.plot_id,
                    analogue_plot_id=analogue.plot_id,
                    run_date=run_date,
                    rank=rank,
                    distance=round(float(dists[j]), 6),
                    same_cluster=same,
                ))

            logger.debug(
                "[Fase 7] Parcela %s... → top-%d análogas calculadas.",
                str(agg.plot_id)[:8], top_n,
            )

        logger.info(
            "[Fase 7] %d registros de análogas generados para %d parcelas (top-%d).",
            len(results), n, top_n,
        )
        return results


analogue_service = AnalogueService()
