from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class CropCreate(BaseModel):
    name: str
    description: str | None = None


class CropUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class CropResponse(BaseModel):
    id: UUID
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)
