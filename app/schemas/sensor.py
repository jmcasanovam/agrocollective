from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class SensorCreate(BaseModel):
    name: str
    sensor_type: str
    unit: str
    description: str | None = None


class SensorUpdate(BaseModel):
    name: str | None = None
    sensor_type: str | None = None
    unit: str | None = None
    description: str | None = None
    is_active: bool | None = None


class SensorResponse(BaseModel):
    id: UUID
    name: str
    sensor_type: str
    unit: str
    description: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class DeviceSensorAssign(BaseModel):
    sensor_ids: list[UUID]
