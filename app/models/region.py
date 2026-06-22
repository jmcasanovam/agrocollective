from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class Region(Base, BaseModelMixin):

    __tablename__ = "regions"

    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    siar_station_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    plots = relationship(
        "Plot",
        back_populates="region"
    )
