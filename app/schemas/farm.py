from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class FarmBase(BaseModel):

    name: str

    latitude: float | None = None

    longitude: float | None = None

    province: str | None = None

    area_ha: float


class FarmCreate(FarmBase):
    pass


class FarmResponse(FarmBase):

    id: UUID

    user_id: UUID

    model_config = ConfigDict(
        from_attributes=True
    )

class FarmUpdate(BaseModel):

    name: str | None = None

    latitude: float | None = None

    longitude: float | None = None

    province: str | None = None

    area_ha: float | None = None