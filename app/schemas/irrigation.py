from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IrrigationCreate(BaseModel):
    week_start: date
    irrigation_mm: float = Field(gt=0)


class IrrigationResponse(BaseModel):
    id: UUID
    plot_id: UUID
    week_start: date
    irrigation_mm: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
