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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_plot_or_404(db, plot_id, current_user.id)

    from app.models.plot_anomaly import PlotAnomaly

    query = db.query(PlotAnomaly).filter(PlotAnomaly.plot_id == plot_id)
    if run_date:
        query = query.filter(PlotAnomaly.run_date == run_date)
    rows = query.order_by(PlotAnomaly.run_date.desc()).all()

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
        latest = (
            db.query(PlotAnalogue.run_date)
            .filter(PlotAnalogue.plot_id == plot_id)
            .order_by(PlotAnalogue.run_date.desc())
            .scalar()
        )
        results = analogue_repository.get_analogues_for_plot(db, plot_id, latest) if latest else []

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
        latest = (
            db.query(PlotMlPrediction.run_date)
            .filter(PlotMlPrediction.plot_id == plot_id)
            .order_by(PlotMlPrediction.run_date.desc())
            .scalar()
        )
        results = ml_prediction_repository.get_by_plot_and_date(db, plot_id, latest) if latest else []

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
