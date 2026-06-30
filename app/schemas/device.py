from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from app.schemas.sensor import SensorResponse


class DeviceCreate(BaseModel):
    code: str


class DeviceResponse(BaseModel):
    id: UUID
    plot_id: UUID
    code: str | None
    is_active: bool
    last_seen_at: datetime | None = None
    battery_mv: int | None = None
    sensors: list[SensorResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DeviceUpdate(BaseModel):
    code: str | None = None
    is_active: bool | None = None
