from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class PlotBase(BaseModel):
    crop_id: UUID
    soil_id: UUID
    name: str | None = None
    area_ha: float | None = None
    management_profile: str | None = None


class PlotCreate(PlotBase):
    pass


class PlotResponse(PlotBase):
    id: UUID
    farm_id: UUID
    hash_plot: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PlotUpdate(BaseModel):
    crop_id: UUID | None = None
    soil_id: UUID | None = None
    name: str | None = None
    area_ha: float | None = None
    management_profile: str | None = None
