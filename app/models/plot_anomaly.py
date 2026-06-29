from datetime import date
from uuid import UUID as PyUUID

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class PlotAnomaly(Base, BaseModelMixin):
    """Anomalía detectada en una parcela dentro de su cluster (LOF)."""

    __tablename__ = "plot_anomalies"

    plot_id: Mapped[PyUUID] = mapped_column(ForeignKey("plots.id"), nullable=False)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)

    lof_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Campos anómalos detectados (texto libre, ej: "soil_humidity,total_water_mm")
    anomalous_features: Mapped[str | None] = mapped_column(Text)

    plot = relationship("Plot", backref="anomalies")
