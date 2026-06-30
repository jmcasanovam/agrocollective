from datetime import date
from uuid import UUID as PyUUID

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class PlotPerformanceHistory(Base, BaseModelMixin):
    """
    Instantánea del rendimiento de una parcela al cierre de cada ejecución del pipeline.

    Consolida variables agregadas, resultado del clustering, anomalía,
    predicción ML y conteo de recomendaciones en un único registro por
    (plot_id, run_date). Permite analizar tendencias temporales por parcela.
    """

    __tablename__ = "plot_performance_history"

    plot_id: Mapped[PyUUID] = mapped_column(ForeignKey("plots.id"), nullable=False)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Cluster asignado (Fase 4)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Variables sensoriales agregadas (Fase 3)
    avg_soil_humidity: Mapped[float | None] = mapped_column(Float)
    avg_air_temp: Mapped[float | None] = mapped_column(Float)
    avg_soil_temp: Mapped[float | None] = mapped_column(Float)
    avg_air_humidity: Mapped[float | None] = mapped_column(Float)

    # Variables de riego y cosecha (Fase 3)
    irrigation_frequency: Mapped[int | None] = mapped_column(Integer)
    avg_irrigation_mm: Mapped[float | None] = mapped_column(Float)
    total_water_mm: Mapped[float | None] = mapped_column(Float)
    yield_kg_ha: Mapped[float | None] = mapped_column(Float)
    water_efficiency: Mapped[float | None] = mapped_column(Float)

    # Anomalía (Fase 5)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lof_score: Mapped[float | None] = mapped_column(Float)

    # Predicciones ML (Fase 8)
    predicted_yield: Mapped[float | None] = mapped_column(Float)
    predicted_efficiency: Mapped[float | None] = mapped_column(Float)

    # Resumen de recomendaciones (Fase 9)
    n_recommendations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_high_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    plot = relationship("Plot", backref="performance_history")
