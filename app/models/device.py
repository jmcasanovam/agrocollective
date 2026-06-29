from uuid import UUID as PyUUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class Device(Base, BaseModelMixin):

    __tablename__ = "devices"

    plot_id: Mapped[PyUUID] = mapped_column(ForeignKey("plots.id"), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    plot = relationship("Plot", back_populates="devices")
    sensors = relationship(
        "Sensor",
        secondary="device_sensors",
        back_populates="devices",
    )
