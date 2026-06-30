from datetime import date
from uuid import UUID as PyUUID

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class PlotCausalResult(Base, BaseModelMixin):
    """Resultado del análisis causal para una parcela anómala."""

    __tablename__ = "plot_causal_results"

    plot_id: Mapped[PyUUID] = mapped_column(ForeignKey("plots.id"), nullable=False)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Feature que presenta la anomalía (ej: "soil_humidity")
    anomalous_feature: Mapped[str] = mapped_column(String(60), nullable=False)
    # Feature identificada como causa probable (ej: "irrigation_mm")
    causal_feature: Mapped[str | None] = mapped_column(String(60))
    # Correlación de Pearson entre ambas series (−1 a 1)
    correlation: Mapped[float | None] = mapped_column(Float)
    # Explicación legible generada automáticamente
    explanation: Mapped[str | None] = mapped_column(Text)

    plot = relationship("Plot", backref="causal_results")
