from uuid import UUID as PyUUID

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class Farm(Base, BaseModelMixin):

    __tablename__ = "farms"

    user_id: Mapped[PyUUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    region_id: Mapped[PyUUID | None] = mapped_column(ForeignKey("regions.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    area_ha: Mapped[float | None] = mapped_column(Float)

    user = relationship("User", back_populates="farms")
    region = relationship("Region", back_populates="farms")
    plots = relationship("Plot", back_populates="farm", cascade="all, delete-orphan")
