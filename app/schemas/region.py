from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class RegionCreate(BaseModel):
    code: str
    name: str
    latitude: float | None = None
    longitude: float | None = None
    siar_station_code: str | None = None


class RegionUpdate(BaseModel):
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    siar_station_code: str | None = None


class RegionResponse(BaseModel):
    id: UUID
    code: str
    name: str
    latitude: float | None
    longitude: float | None
    siar_station_code: str | None

    model_config = ConfigDict(from_attributes=True)
