from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class FarmBase(BaseModel):
    name: str
    region_id: UUID | None = None
    latitude: float | None = None
    longitude: float | None = None
    area_ha: float | None = None


class FarmCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    region_id: UUID
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    area_ha: float = Field(gt=0, le=100000)


class FarmResponse(FarmBase):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


class FarmUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    region_id: UUID | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area_ha: float | None = Field(default=None, gt=0, le=100000)
