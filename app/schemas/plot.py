from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class PlotBase(BaseModel):
    crop_id: UUID
    soil_id: UUID
    name: str | None = None
    area_ha: float | None = None
    management_profile: str | None = None


class PlotCreate(BaseModel):
    crop_id: UUID
    soil_id: UUID
    name: str = Field(min_length=2, max_length=150)
    area_ha: float = Field(gt=0, le=100000)
    management_profile: str | None = None


class PlotResponse(PlotBase):
    id: UUID
    farm_id: UUID
    hash_plot: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PlotUpdate(BaseModel):
    crop_id: UUID | None = None
    soil_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=150)
    area_ha: float | None = Field(default=None, gt=0, le=100000)
    management_profile: str | None = None
