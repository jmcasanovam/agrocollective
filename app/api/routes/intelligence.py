"""
Endpoints de inteligencia agronómica por parcela.

Todos los endpoints:
  - Requieren autenticación JWT.
  - Verifican que la parcela pertenece al usuario autenticado.
  - Devuelven los resultados del último run_date disponible por defecto,
    o de un run_date concreto si se pasa como query param.

Rutas:
  GET /plots/{plot_id}/recommendations
  GET /plots/{plot_id}/anomalies
  GET /plots/{plot_id}/analogues
  GET /plots/{plot_id}/ml-predictions
  GET /plots/{plot_id}/performance-history
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.plot_repository import plot_repository
from app.repositories.recommendation_repository import recommendation_repository
from app.repositories.anomaly_repository import anomaly_repository
from app.repositories.analogue_repository import analogue_repository
from app.repositories.ml_prediction_repository import ml_prediction_repository
from app.repositories.performance_history_repository import performance_history_repository
from app.schemas.intelligence import (
    AnomalyResponse,
    AnalogueResponse,
    MlPredictionResponse,
    PerformanceHistoryResponse,
    RecommendationResponse,
)

router = APIRouter(tags=["Intelligence"])


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_plot_or_404(db: Session, plot_id: UUID, user_id: UUID):
    plot = plot_repository.get_by_id_and_user(db, plot_id, user_id)
    if not plot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcela no encontrada o sin acceso.",
        )
    return plot


# ─────────────────────────────────────────────────────────────────────────────
# Recomendaciones
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/plots/{plot_id}/recommendations",
    response_model=list[RecommendationResponse],
    summary="Recomendaciones agronómicas de la parcela",
    description=(
        "Devuelve las recomendaciones del último pipeline ejecutado (o de un "
        "`run_date` concreto). Ordenadas por prioridad: high → medium → low."
    ),
)
def get_recommendations(
    plot_id: UUID,
    run_date: date | None = Query(default=None, description="Filtrar por fecha de ejecución (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_plot_or_404(db, plot_id, current_user.id)

    if run_date:
        results = recommendation_repository.get_by_plot_and_date(db, plot_id, run_date)
    else:
        results = recommendation_repository.get_latest_by_plot(db, plot_id)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Anomalías
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/plots/{plot_id}/anomalies",
    response_model=list[AnomalyResponse],
    summary="Historial de detección de anomalías de la parcela",
    description=(
        "Devuelve los registros LOF de la parcela. Sin `run_date` devuelve "
        "todos los registros ordenados del más reciente al más antiguo."
    ),
)
def get_anomalies(
    plot_id: UUID,
    run_date: date | None = Query(default=None, description="Filtrar por fecha de ejecución (YYYY-MM-DD)"),
    limit: int = Query(default=100, ge=1, le=500, description="Número máximo de registros a devolver"),
    offset: int = Query(default=0, ge=0, description="Registros a saltar (paginación)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_plot_or_404(db, plot_id, current_user.id)

    from app.models.plot_anomaly import PlotAnomaly

    query = db.query(PlotAnomaly).filter(PlotAnomaly.plot_id == plot_id)
    if run_date:
        query = query.filter(PlotAnomaly.run_date == run_date)
    rows = query.order_by(PlotAnomaly.run_date.desc()).offset(offset).limit(limit).all()

    return [AnomalyResponse.from_orm_with_features(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Parcelas análogas
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/plots/{plot_id}/analogues",
    response_model=list[AnalogueResponse],
    summary="Parcelas más similares a esta parcela",
    description=(
        "Devuelve las parcelas análogas del último run_date (o uno concreto), "
        "ordenadas por distancia ascendente (rank 1 = más parecida)."
    ),
)
def get_analogues(
    plot_id: UUID,
    run_date: date | None = Query(default=None, description="Filtrar por fecha de ejecución (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_plot_or_404(db, plot_id, current_user.id)

    if run_date:
        results = analogue_repository.get_analogues_for_plot(db, plot_id, run_date)
    else:
        # Último run_date disponible
        from app.models.plot_analogue import PlotAnalogue
        row = (
            db.query(PlotAnalogue.run_date)
            .filter(PlotAnalogue.plot_id == plot_id)
            .order_by(PlotAnalogue.run_date.desc())
            .first()
        )
        results = analogue_repository.get_analogues_for_plot(db, plot_id, row.run_date) if row else []

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Predicciones ML
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/plots/{plot_id}/ml-predictions",
    response_model=list[MlPredictionResponse],
    summary="Predicciones ML de rendimiento y eficiencia hídrica",
    description=(
        "Devuelve las predicciones Random Forest del último pipeline "
        "(yield_kg_ha y water_efficiency). `predicted_value` puede ser null "
        "si no había suficientes muestras de entrenamiento."
    ),
)
def get_ml_predictions(
    plot_id: UUID,
    run_date: date | None = Query(default=None, description="Filtrar por fecha de ejecución (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_plot_or_404(db, plot_id, current_user.id)

    if run_date:
        results = ml_prediction_repository.get_by_plot_and_date(db, plot_id, run_date)
    else:
        from app.models.plot_ml_prediction import PlotMlPrediction
        row = (
            db.query(PlotMlPrediction.run_date)
            .filter(PlotMlPrediction.plot_id == plot_id)
            .order_by(PlotMlPrediction.run_date.desc())
            .first()
        )
        results = ml_prediction_repository.get_by_plot_and_date(db, plot_id, row.run_date) if row else []

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Historial de rendimiento
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/plots/{plot_id}/performance-history",
    response_model=list[PerformanceHistoryResponse],
    summary="Historial de rendimiento de la parcela",
    description=(
        "Devuelve las instantáneas del pipeline nocturno ordenadas del más "
        "reciente al más antiguo. Usa `limit` para controlar cuántos registros "
        "devolver (default: 90, equivale a ~3 meses de ejecuciones diarias)."
    ),
)
def get_performance_history(
    plot_id: UUID,
    limit: int = Query(default=90, ge=1, le=365, description="Número máximo de registros a devolver"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_plot_or_404(db, plot_id, current_user.id)
    return performance_history_repository.get_history_for_plot(db, plot_id, limit)


# ─────────────────────────────────────────────────────────────────────────────
# Datos de Clima SiAR
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/plots/{plot_id}/weather",
    response_model=list[dict]
)
def get_plot_weather_history(
    plot_id: UUID,
    year: int | None = Query(default=None, ge=2025, le=2100, description="Filtrar por año (requiere 'month')"),
    month: int | None = Query(default=None, ge=1, le=12, description="Filtrar por mes (requiere 'year')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Devuelve los registros climáticos SiAR de la estación asociada a la
    parcela del usuario. Sin filtro: últimos 30 días (más reciente primero).
    Con year+month: todo ese mes natural (orden cronológico ascendente).
    """
    plot = _get_plot_or_404(db, plot_id, current_user.id)
    farm = plot.farm
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La parcela no está asociada a ninguna finca."
        )

    from app.services.regions.region_resolver import resolve_region_for_farm

    region = resolve_region_for_farm(db, farm)
    station_code = region.siar_station_code if region else None
    if not station_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay ninguna región con estación SiAR configurada en el catálogo."
        )

    # Consultar InfluxDB
    from app.database.influx import get_influx_client, get_query_api
    from app.core.config import settings

    if year is not None and month is not None:
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        range_clause = f"start: {year:04d}-{month:02d}-01T00:00:00Z, stop: {next_year:04d}-{next_month:02d}-01T00:00:00Z"
        sort_desc = "false"
        limit_clause = "|> limit(n: 31)"
    else:
        range_clause = "start: 2025-06-01T00:00:00Z"
        sort_desc = "true"
        limit_clause = "|> limit(n: 30)"

    flux = f"""
    from(bucket: "{settings.INFLUXDB_BUCKET_WEATHER}")
      |> range({range_clause})
      |> filter(fn: (r) => r._measurement == "weather")
      |> filter(fn: (r) => r.siar_station_code == "{station_code}")
      |> pivot(
           rowKey:    ["_time", "siar_station_code"],
           columnKey: ["_field"],
           valueColumn: "_value"
         )
      |> sort(columns: ["_time"], desc: {sort_desc})
      {limit_clause}
    """

    results = []
    try:
        client = get_influx_client()
        try:
            tables = get_query_api(client).query(flux, org=settings.INFLUXDB_ORG)
            for table in tables:
                for record in table.records:
                    row = record.values
                    results.append({
                        "date": row.get("_time").strftime("%Y-%m-%d") if row.get("_time") else None,
                        "station_code": row.get("siar_station_code"),
                        "air_temp": row.get("air_temp"),
                        "air_temp_max": row.get("air_temp_max"),
                        "air_temp_min": row.get("air_temp_min"),
                        "relative_humidity": row.get("relative_humidity"),
                        "relative_humidity_max": row.get("relative_humidity_max"),
                        "relative_humidity_min": row.get("relative_humidity_min"),
                        "soil_temp": row.get("soil_temp"),
                        "eto": row.get("eto"),
                        "precipitation": row.get("precipitation"),
                    })
        finally:
            client.close()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar datos SiAR desde InfluxDB: {exc}"
        )

    return results
