from datetime import date
from uuid import UUID as PyUUID

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class PlotAnalogue(Base, BaseModelMixin):
    """Parcela análoga más cercana en el espacio de features normalizado."""

    __tablename__ = "plot_analogues"

    plot_id: Mapped[PyUUID] = mapped_column(ForeignKey("plots.id"), nullable=False)
    analogue_plot_id: Mapped[PyUUID] = mapped_column(ForeignKey("plots.id"), nullable=False)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    distance: Mapped[float] = mapped_column(Float, nullable=False)
    same_cluster: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    plot = relationship("Plot", foreign_keys=[plot_id], backref="analogues")
    analogue_plot = relationship("Plot", foreign_keys=[analogue_plot_id])
