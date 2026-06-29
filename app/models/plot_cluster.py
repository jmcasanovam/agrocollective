from datetime import date
from uuid import UUID as PyUUID

from sqlalchemy import Date, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class PlotCluster(Base, BaseModelMixin):
    """Asignación de una parcela a un cluster en una ejecución concreta."""

    __tablename__ = "plot_clusters"

    plot_id: Mapped[PyUUID] = mapped_column(ForeignKey("plots.id"), nullable=False)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)

    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_to_centroid: Mapped[float | None] = mapped_column(Float)

    # Estadísticas del cluster al que pertenece (desnormalizadas para consulta rápida)
    cluster_size: Mapped[int | None] = mapped_column(Integer)
    cluster_avg_soil_humidity: Mapped[float | None] = mapped_column(Float)
    cluster_avg_air_temp: Mapped[float | None] = mapped_column(Float)
    cluster_avg_irrigation_mm: Mapped[float | None] = mapped_column(Float)
    cluster_avg_efficiency: Mapped[float | None] = mapped_column(Float)

    plot = relationship("Plot", backref="clusters")
