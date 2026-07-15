from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HarvestCreate(BaseModel):
    harvest_date: date
    yield_kg_ha: float | None = None
    water_consumed_m3_ha: float | None = None


class HarvestResponse(BaseModel):
    id: UUID
    plot_id: UUID
    harvest_date: date
    yield_kg_ha: float | None
    water_consumed_m3_ha: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
