from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.harvest_repository import harvest_repository
from app.repositories.plot_repository import plot_repository
from app.schemas.harvest import HarvestCreate, HarvestResponse

router = APIRouter(prefix="/plots/{plot_id}/harvests", tags=["Harvests"])


def _get_plot_or_404(db: Session, plot_id: UUID, user_id: UUID):
    plot = plot_repository.get_by_id_and_user(db, plot_id, user_id)
    if not plot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcela no encontrada o sin acceso.",
        )
    return plot


@router.get("", response_model=list[HarvestResponse])
def get_harvests(
    plot_id: UUID,
    limit: int = Query(default=100, ge=1, le=500, description="Numero maximo de registros a devolver"),
    offset: int = Query(default=0, ge=0, description="Registros a saltar (paginacion)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_plot_or_404(db, plot_id, current_user.id)
    return harvest_repository.get_all_by_plot(db, plot_id, limit, offset)


@router.post("", response_model=HarvestResponse, status_code=status.HTTP_201_CREATED)
def create_harvest(
    plot_id: UUID,
    data: HarvestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_plot_or_404(db, plot_id, current_user.id)

    if harvest_repository.get_by_plot_and_date(db, plot_id, data.harvest_date):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cosecha registrada para esa fecha.",
        )

    return harvest_repository.create(db, plot_id, data)
