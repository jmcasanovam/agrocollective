"""Persiste los resultados de clustering en PostgreSQL (tabla plot_clusters)."""

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.models.plot_cluster import PlotCluster
from app.services.clustering.kmeans_service import ClusteringResult

logger = logging.getLogger(__name__)


def save_clustering_result(db: Session, result: ClusteringResult) -> None:
    """
    Guarda las asignaciones de cluster en la tabla plot_clusters.
    Elimina las asignaciones anteriores del mismo run_date antes de insertar.
    """
    if not result.assignments:
        logger.info("Sin asignaciones de cluster que guardar.")
        return

    # Borrar asignaciones previas del mismo día para idempotencia
    deleted = (
        db.query(PlotCluster)
        .filter(PlotCluster.run_date == result.run_date)
        .delete()
    )
    if deleted:
        logger.debug("Borradas %d asignaciones previas de %s.", deleted, result.run_date)

    # Insertar nuevas asignaciones
    for a in result.assignments:
        db.add(PlotCluster(
            plot_id=a.plot_id,
            run_date=result.run_date,
            cluster_id=a.cluster_id,
            distance_to_centroid=a.distance_to_centroid,
            cluster_size=a.cluster_size,
            cluster_avg_soil_humidity=a.cluster_avg_soil_humidity,
            cluster_avg_air_temp=a.cluster_avg_air_temp,
            cluster_avg_irrigation_mm=a.cluster_avg_irrigation_mm,
            cluster_avg_efficiency=a.cluster_avg_efficiency,
        ))

    db.commit()
    logger.info(
        "Clustering guardado | run_date=%s | k=%d | parcelas=%d",
        result.run_date, result.n_clusters, len(result.assignments),
    )
