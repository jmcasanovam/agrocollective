from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


device_sensors = Table(
    "device_sensors",
    Base.metadata,
    Column(
        "device_id",
        PGUUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "sensor_id",
        PGUUID(as_uuid=True),
        ForeignKey("sensors.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Sensor(Base, BaseModelMixin):

    __tablename__ = "sensors"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    devices = relationship("Device", secondary=device_sensors, back_populates="sensors")
