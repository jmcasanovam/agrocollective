from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class Device(Base, BaseModelMixin):

    __tablename__ = "devices"

    plot_id: Mapped[UUID] = mapped_column(
        ForeignKey("plots.id"),
        nullable=False
    )

    esp32_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="inactive",
        nullable=False
    )

    battery_mv: Mapped[int | None] = mapped_column(Integer)

    last_reading: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    plot = relationship(
        "Plot",
        back_populates="devices"
    )
