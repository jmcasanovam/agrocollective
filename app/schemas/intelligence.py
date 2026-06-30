"""Schemas de respuesta para los endpoints de inteligencia agronómica."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecommendationResponse(BaseModel):
    id: UUID
    plot_id: UUID
    run_date: date
    category: str
    priority: str
    title: str
    body: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnomalyResponse(BaseModel):
    id: UUID
    plot_id: UUID
    run_date: date
    cluster_id: int
    lof_score: float
    is_anomaly: bool
    anomalous_features: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_features(cls, obj) -> "AnomalyResponse":
        features = (
            [f.strip() for f in obj.anomalous_features.split(",") if f.strip()]
            if obj.anomalous_features
            else []
        )
        return cls(
            id=obj.id,
            plot_id=obj.plot_id,
            run_date=obj.run_date,
            cluster_id=obj.cluster_id,
            lof_score=obj.lof_score,
            is_anomaly=obj.is_anomaly,
            anomalous_features=features,
            created_at=obj.created_at,
        )


class AnalogueResponse(BaseModel):
    id: UUID
    plot_id: UUID
    analogue_plot_id: UUID
    run_date: date
    rank: int
    distance: float
    same_cluster: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MlPredictionResponse(BaseModel):
    id: UUID
    plot_id: UUID
    run_date: date
    cluster_id: int
    target: str
    predicted_value: float | None
    model_r2: float | None
    n_training_samples: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PerformanceHistoryResponse(BaseModel):
    id: UUID
    plot_id: UUID
    run_date: date
    cluster_id: int
    avg_soil_humidity: float | None
    avg_air_temp: float | None
    avg_soil_temp: float | None
    avg_air_humidity: float | None
    irrigation_frequency: int | None
    avg_irrigation_mm: float | None
    total_water_mm: float | None
    yield_kg_ha: float | None
    water_efficiency: float | None
    is_anomaly: bool
    lof_score: float | None
    predicted_yield: float | None
    predicted_efficiency: float | None
    n_recommendations: int
    n_high_priority: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
