from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class Harvest(Base, BaseModelMixin):

    __tablename__ = "harvests"

    plot_id: Mapped[UUID] = mapped_column(
        ForeignKey("plots.id"),
        nullable=False
    )

    campaign: Mapped[str | None] = mapped_column(String(50))

    production_kg: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    production_kg_ha: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    water_consumption_m3_ha: Mapped[float | None] = mapped_column(Float)

    harvest_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    plot = relationship(
        "Plot",
        back_populates="harvests"
    )
