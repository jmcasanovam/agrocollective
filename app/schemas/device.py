from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class DeviceCreate(BaseModel):

    esp32_id: str


class DeviceResponse(BaseModel):

    id: UUID

    plot_id: UUID

    esp32_id: str

    status: str

    battery_mv: int | None

    last_reading: datetime | None

    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class DeviceUpdate(BaseModel):

    status: str | None = None

    battery_mv: int | None = None
