from datetime import date

from sqlalchemy import Date, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class IrrigationWeekly(Base, BaseModelMixin):

    __tablename__ = "irrigation_weekly"

    plot_id: Mapped[UUID] = mapped_column(
        ForeignKey("plots.id"),
        nullable=False
    )

    week_start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    irrigation_mm: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    plot = relationship(
        "Plot",
        back_populates="irrigation_records"
    )
