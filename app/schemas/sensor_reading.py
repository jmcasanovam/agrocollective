from datetime import datetime

from pydantic import BaseModel


class SensorReadingPoint(BaseModel):
    sensor: str
    value: float
    recorded_at: datetime
