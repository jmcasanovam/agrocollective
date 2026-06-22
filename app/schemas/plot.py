from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class PlotBase(BaseModel):

    crop_id: UUID

    soil_id: UUID

    region_id: UUID

    area_ha: float

    depth_cm: int | None = None

    name: str


class PlotCreate(PlotBase):
    pass


class PlotResponse(PlotBase):

    id: UUID

    farm_id: UUID

    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class PlotUpdate(BaseModel):

    crop_id: UUID | None = None

    soil_id: UUID | None = None

    region_id: UUID | None = None

    area_ha: float | None = None

    depth_cm: int | None = None

    name: str | None = None
