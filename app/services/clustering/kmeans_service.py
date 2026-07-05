"""
Fase 4: Clustering K-Means de parcelas.

Agrupa las parcelas en clusters según sus variables agronómicas.
Maneja el caso borde de N < k reduciendo k automáticamente.

Variables de entrada (PlotAggregates):
  - avg_soil_humidity, avg_air_temp, avg_soil_temp, avg_air_humidity
  - irrigation_frequency, avg_irrigation_mm, total_water_mm
  - yield_kg_ha, water_efficiency

Salida (list[PlotClusterResult]):
  - plot_id, cluster_id, distance_to_centroid
  - estadísticas del cluster (size, medias)
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import UUID

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from app.core.config import settings
from app.services.measurements.aggregation_service import PlotAggregates

logger = logging.getLogger(__name__)

# Columnas del vector de features en orden fijo
FEATURE_COLUMNS = [
    "avg_soil_humidity",
    "avg_air_temp",
    "avg_soil_temp",
    "avg_air_humidity",
    "irrigation_frequency",
    "avg_irrigation_mm",
    "total_water_mm",
    "yield_kg_ha",
    "water_efficiency",
]


@dataclass
class PlotClusterResult:
    plot_id: UUID
    hash_plot: str
    cluster_id: int
    distance_to_centroid: float

    # Estadísticas del cluster al que pertenece
    cluster_size: int = 0
    cluster_avg_soil_humidity: float | None = None
    cluster_avg_air_temp: float | None = None
    cluster_avg_irrigation_mm: float | None = None
    cluster_avg_efficiency: float | None = None


@dataclass
class ClusteringResult:
    run_date: date
    n_clusters: int
    n_plots: int
    inertia: float | None
    assignments: list[PlotClusterResult] = field(default_factory=list)


class KMeansService:

    def run(self, aggregates: list[PlotAggregates]) -> ClusteringResult:
        """
        Ejecuta K-Means sobre la lista de PlotAggregates.

        Si hay menos parcelas que el k configurado, reduce k automáticamente.
        Con 1 sola parcela asigna cluster_id=0 sin ejecutar K-Means.

        Returns:
            ClusteringResult con las asignaciones de cluster por parcela.
        """
        run_date = datetime.now(timezone.utc).date()
        n_plots = len(aggregates)

        result = ClusteringResult(
            run_date=run_date,
            n_clusters=0,
            n_plots=n_plots,
            inertia=None,
        )

        if n_plots == 0:
            logger.warning("K-Means: sin parcelas para clusterizar.")
            return result

        # Construir matriz de features (None → 0)
        X = self._build_feature_matrix(aggregates)

        # Determinar k efectivo
        k = min(settings.KMEANS_MAX_CLUSTERS, n_plots)
        result.n_clusters = k

        if k == 1:
            logger.info("K-Means: solo %d parcela(s), asignando cluster único.", n_plots)
            assignments = self._single_cluster(aggregates, X)
            result.assignments = assignments
            return result

        # Normalizar features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Ejecutar K-Means
        logger.info("K-Means: k=%d sobre %d parcelas | features=%s", k, n_plots, FEATURE_COLUMNS)
        kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(X_scaled)
        result.inertia = float(kmeans.inertia_)

        # Calcular distancias al centroide
        distances = self._distances_to_centroids(X_scaled, kmeans.cluster_centers_, labels)

        # Calcular estadísticas por cluster
        cluster_stats = self._cluster_statistics(aggregates, labels, k)

        # Construir asignaciones
        for i, agg in enumerate(aggregates):
            cid = int(labels[i])
            stats = cluster_stats[cid]
            result.assignments.append(PlotClusterResult(
                plot_id=agg.plot_id,
                hash_plot=agg.hash_plot,
                cluster_id=cid,
                distance_to_centroid=round(float(distances[i]), 6),
                cluster_size=stats["size"],
                cluster_avg_soil_humidity=stats["avg_soil_humidity"],
                cluster_avg_air_temp=stats["avg_air_temp"],
                cluster_avg_irrigation_mm=stats["avg_irrigation_mm"],
                cluster_avg_efficiency=stats["avg_efficiency"],
            ))

        for a in result.assignments:
            logger.info(
                "  Parcela %s... → cluster %d (dist=%.4f, cluster_size=%d)",
                str(a.plot_id)[:8], a.cluster_id, a.distance_to_centroid, a.cluster_size,
            )

        logger.info(
            "K-Means completado | k=%d | inertia=%.2f | parcelas=%d",
            k, result.inertia, n_plots
        )
        return result

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _build_feature_matrix(self, aggregates: list[PlotAggregates]) -> np.ndarray:
        """Construye la matriz (n_plots × n_features) con None → 0."""
        rows = []
        for agg in aggregates:
            row = [float(getattr(agg, col) or 0) for col in FEATURE_COLUMNS]
            rows.append(row)
        return np.array(rows, dtype=float)

    def _single_cluster(
        self, aggregates: list[PlotAggregates], X: np.ndarray
    ) -> list[PlotClusterResult]:
        """Caso borde: asigna todas las parcelas al cluster 0 sin ejecutar K-Means."""
        stats = self._cluster_statistics(aggregates, np.zeros(len(aggregates), dtype=int), 1)
        return [
            PlotClusterResult(
                plot_id=agg.plot_id,
                hash_plot=agg.hash_plot,
                cluster_id=0,
                distance_to_centroid=0.0,
                cluster_size=stats[0]["size"],
                cluster_avg_soil_humidity=stats[0]["avg_soil_humidity"],
                cluster_avg_air_temp=stats[0]["avg_air_temp"],
                cluster_avg_irrigation_mm=stats[0]["avg_irrigation_mm"],
                cluster_avg_efficiency=stats[0]["avg_efficiency"],
            )
            for agg in aggregates
        ]

    @staticmethod
    def _distances_to_centroids(
        X_scaled: np.ndarray, centers: np.ndarray, labels: np.ndarray
    ) -> np.ndarray:
        distances = np.zeros(len(labels))
        for i, label in enumerate(labels):
            distances[i] = np.linalg.norm(X_scaled[i] - centers[label])
        return distances

    @staticmethod
    def _cluster_statistics(
        aggregates: list[PlotAggregates], labels: np.ndarray, k: int
    ) -> dict[int, dict]:
        stats: dict[int, dict] = {}
        for cid in range(k):
            members = [agg for i, agg in enumerate(aggregates) if labels[i] == cid]
            if not members:
                stats[cid] = {
                    "size": 0,
                    "avg_soil_humidity": None,
                    "avg_air_temp": None,
                    "avg_irrigation_mm": None,
                    "avg_efficiency": None,
                }
                continue

            def _mean(attr: str) -> float | None:
                vals = [getattr(m, attr) for m in members if getattr(m, attr) is not None]
                return round(sum(vals) / len(vals), 4) if vals else None

            stats[cid] = {
                "size": len(members),
                "avg_soil_humidity": _mean("avg_soil_humidity"),
                "avg_air_temp": _mean("avg_air_temp"),
                "avg_irrigation_mm": _mean("avg_irrigation_mm"),
                "avg_efficiency": _mean("water_efficiency"),
            }
        return stats


kmeans_service = KMeansService()
