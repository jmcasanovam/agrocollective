from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class DeviceCreate(BaseModel):
    code: str


class DeviceResponse(BaseModel):
    id: UUID
    plot_id: UUID
    code: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class DeviceUpdate(BaseModel):
    code: str | None = None
    is_active: bool | None = None
