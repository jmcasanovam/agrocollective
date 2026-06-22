from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class CropResponse(BaseModel):

    id: UUID

    name: str

    description: str | None

    model_config = ConfigDict(from_attributes=True)


class SoilResponse(BaseModel):

    id: UUID

    name: str

    description: str | None

    model_config = ConfigDict(from_attributes=True)


class RegionResponse(BaseModel):

    id: UUID

    code: str

    name: str

    siar_station_code: str

    model_config = ConfigDict(from_attributes=True)
