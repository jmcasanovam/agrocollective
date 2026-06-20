from datetime import datetime

from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import ForeignKey
from sqlalchemy import DateTime
from sqlalchemy import Boolean

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class Sensor(Base, BaseModelMixin):

    __tablename__ = "sensors"

    plot_id: Mapped[UUID] = mapped_column(
        ForeignKey("plots.id"),
        nullable=False
    )

    esp32_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    sensor_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    depth_cm: Mapped[int | None] = mapped_column(
        Integer
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="offline",
        nullable=False
    )

    battery_mv: Mapped[int | None] = mapped_column(
        Integer
    )

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
        back_populates="sensors"
    )