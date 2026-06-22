from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class Plot(Base, BaseModelMixin):

    __tablename__ = "plots"

    farm_id: Mapped[UUID] = mapped_column(
        ForeignKey("farms.id"),
        nullable=False
    )

    crop_id: Mapped[UUID] = mapped_column(
        ForeignKey("crops.id"),
        nullable=False
    )

    soil_id: Mapped[UUID] = mapped_column(
        ForeignKey("soils.id"),
        nullable=False
    )

    region_id: Mapped[UUID] = mapped_column(
        ForeignKey("regions.id"),
        nullable=False
    )

    area_ha: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    depth_cm: Mapped[int | None] = mapped_column(Integer)

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    hash_plot: Mapped[str | None] = mapped_column(String(64))

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    farm = relationship(
        "Farm",
        back_populates="plots"
    )

    crop = relationship(
        "Crop",
        back_populates="plots"
    )

    soil = relationship(
        "Soil",
        back_populates="plots"
    )

    region = relationship(
        "Region",
        back_populates="plots"
    )

    devices = relationship(
        "Device",
        back_populates="plot",
        cascade="all, delete-orphan"
    )

    irrigation_records = relationship(
        "IrrigationWeekly",
        back_populates="plot",
        cascade="all, delete-orphan"
    )

    harvests = relationship(
        "Harvest",
        back_populates="plot",
        cascade="all, delete-orphan"
    )
