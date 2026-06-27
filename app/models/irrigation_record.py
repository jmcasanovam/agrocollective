from datetime import date
from uuid import UUID as PyUUID

from sqlalchemy import Date, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class IrrigationRecord(Base, BaseModelMixin):

    __tablename__ = "irrigation_records"
    __table_args__ = (UniqueConstraint("plot_id", "week_start", name="uq_irrigation_plot_week"),)

    plot_id: Mapped[PyUUID] = mapped_column(ForeignKey("plots.id"), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    irrigation_mm: Mapped[float] = mapped_column(Float, nullable=False)

    plot = relationship("Plot", back_populates="irrigation_records")
