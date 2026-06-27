from datetime import date
from uuid import UUID as PyUUID

from sqlalchemy import Date, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class Harvest(Base, BaseModelMixin):

    __tablename__ = "harvests"

    plot_id: Mapped[PyUUID] = mapped_column(ForeignKey("plots.id"), nullable=False)
    harvest_date: Mapped[date] = mapped_column(Date, nullable=False)
    yield_kg_ha: Mapped[float | None] = mapped_column(Float)
    water_consumed_m3_ha: Mapped[float | None] = mapped_column(Float)

    plot = relationship("Plot", back_populates="harvests")
