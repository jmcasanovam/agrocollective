from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class SensorType(str, Enum):

    soil_moisture = "soil_moisture"
    temperature = "temperature"
    humidity = "humidity"
    conductivity = "conductivity"
    ph = "ph"


class SensorBase(BaseModel):

    esp32_id: str

    sensor_type: SensorType

    depth_cm: int | None = None


class SensorCreate(SensorBase):
    pass


class SensorResponse(SensorBase):

    id: UUID

    plot_id: UUID

    status: str

    battery_mv: int | None

    last_reading: datetime | None

    is_active: bool

    model_config = ConfigDict(
        from_attributes=True
    )

class SensorUpdate(BaseModel):

    sensor_type: SensorType | None = None

    depth_cm: int | None = None

    status: str | None = None