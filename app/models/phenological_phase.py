from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class PhenologicalPhase(Base, BaseModelMixin):

    __tablename__ = "phenological_phases"

    crop_id: Mapped[UUID] = mapped_column(
        ForeignKey("crops.id"),
        nullable=False
    )

    phase_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    typical_start_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    typical_end_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    notes: Mapped[str | None] = mapped_column(Text)

    crop = relationship(
        "Crop",
        back_populates="phenological_phases"
    )
