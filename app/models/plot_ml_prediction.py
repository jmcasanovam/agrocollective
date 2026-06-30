from datetime import date
from uuid import UUID as PyUUID

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class PlotMlPrediction(Base, BaseModelMixin):
    """Predicción ML de rendimiento y eficiencia hídrica para una parcela."""

    __tablename__ = "plot_ml_predictions"

    plot_id: Mapped[PyUUID] = mapped_column(ForeignKey("plots.id"), nullable=False)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Variable objetivo predicha
    target: Mapped[str] = mapped_column(String(40), nullable=False)       # "yield_kg_ha" | "water_efficiency"
    predicted_value: Mapped[float | None] = mapped_column(Float)
    model_r2: Mapped[float | None] = mapped_column(Float)                  # R² del modelo (OOB o CV)
    n_training_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    plot = relationship("Plot", backref="ml_predictions")
