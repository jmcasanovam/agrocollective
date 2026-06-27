from uuid import UUID as PyUUID

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class Plot(Base, BaseModelMixin):

    __tablename__ = "plots"

    farm_id: Mapped[PyUUID] = mapped_column(ForeignKey("farms.id"), nullable=False)
    crop_id: Mapped[PyUUID] = mapped_column(ForeignKey("crops.id"), nullable=False)
    soil_id: Mapped[PyUUID] = mapped_column(ForeignKey("soils.id"), nullable=False)

    name: Mapped[str | None] = mapped_column(String(150))
    area_ha: Mapped[float | None] = mapped_column(Float)
    hash_plot: Mapped[str | None] = mapped_column(String(64))
    management_profile: Mapped[str | None] = mapped_column(String(20))

    farm = relationship("Farm", back_populates="plots")
    crop = relationship("Crop", back_populates="plots")
    soil = relationship("Soil", back_populates="plots")
    devices = relationship("Device", back_populates="plot", cascade="all, delete-orphan")
    irrigation_records = relationship("IrrigationRecord", back_populates="plot", cascade="all, delete-orphan")
    harvests = relationship("Harvest", back_populates="plot", cascade="all, delete-orphan")
