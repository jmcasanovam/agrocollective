from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class Farm(Base, BaseModelMixin):

    __tablename__ = "farms"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    latitude: Mapped[float | None] = mapped_column(
        Float
    )

    longitude: Mapped[float | None] = mapped_column(
        Float
    )

    province: Mapped[str | None] = mapped_column(
        String(100)
    )

    area_ha: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="farms"
    )

    plots = relationship(
        "Plot",
        back_populates="farm",
        cascade="all, delete-orphan"
    )