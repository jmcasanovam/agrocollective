from datetime import date
from uuid import UUID as PyUUID

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class PlotRecommendation(Base, BaseModelMixin):
    """Recomendación agronómica generada por el pipeline inteligente."""

    __tablename__ = "plot_recommendations"

    plot_id: Mapped[PyUUID] = mapped_column(ForeignKey("plots.id"), nullable=False)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Origen de la recomendación
    category: Mapped[str] = mapped_column(String(20), nullable=False)   # anomaly | prediction | benchmark
    priority: Mapped[str] = mapped_column(String(10), nullable=False)   # high | medium | low

    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    plot = relationship("Plot", backref="recommendations")
