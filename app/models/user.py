from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.models.mixins import BaseModelMixin


class User(Base, BaseModelMixin):

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    region: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    farms = relationship(
        "Farm",
        back_populates="user"
    )