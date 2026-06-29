from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class SoilCreate(BaseModel):
    name: str
    description: str | None = None


class SoilUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class SoilResponse(BaseModel):
    id: UUID
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)
