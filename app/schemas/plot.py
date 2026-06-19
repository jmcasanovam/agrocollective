from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class PlotBase(BaseModel):

    crop_type: str

    soil_type: str

    area_ha: float

    depth_cm: int | None = None

    province: str | None = None

    name: str


class PlotCreate(PlotBase):
    pass


class PlotResponse(PlotBase):

    id: UUID

    farm_id: UUID

    is_active: bool

    model_config = ConfigDict(
        from_attributes=True
    )