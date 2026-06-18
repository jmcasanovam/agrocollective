from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class Plot(Base, BaseModelMixin):

    __tablename__ = "plots"

    farm_id: Mapped[UUID] = mapped_column(
        ForeignKey("farms.id"),
        nullable=False
    )

    crop_type: Mapped[str] = mapped_column(
        String(100)
    )

    soil_type: Mapped[str] = mapped_column(
        String(100)
    )

    area_ha: Mapped[float] = mapped_column(
        Float
    )

    depth_cm: Mapped[int | None] = mapped_column(
        Integer
    )

    province: Mapped[str | None] = mapped_column(
        String(100)
    )

    farm = relationship(
        "Farm",
        back_populates="plots"
    )