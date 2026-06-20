from fastapi import APIRouter
from fastapi import Depends
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.dependencies import get_current_user

from app.models.user import User

from app.schemas.plot import PlotCreate
from app.schemas.plot import PlotUpdate
from app.schemas.plot import PlotResponse

from app.services.plots.plot_service import plot_service


router = APIRouter(
    prefix="/farms/{farm_id}/plots",
    tags=["Plots"]
)


@router.post(
    "",
    response_model=PlotResponse
)
def create_plot(
    farm_id: UUID,
    plot_data: PlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return plot_service.create(
        db,
        plot_data,
        farm_id,
        current_user.id
    )



@router.get(
    "",
    response_model=list[PlotResponse]
)
def get_plots(
    farm_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return plot_service.get_all(
        db,
        farm_id,
        current_user.id
    )


@router.put(
    "/{plot_id}",
    response_model=PlotResponse
)
def update_plot(
    farm_id: UUID,
    plot_id: UUID,
    plot_data: PlotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return plot_service.update(
        db,
        farm_id,
        plot_id,
        plot_data,
        current_user.id
    )


@router.delete(
    "/{plot_id}"
)
def delete_plot(
    farm_id: UUID,
    plot_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    plot_service.delete(
        db,
        farm_id,
        plot_id,
        current_user.id
    )

    return {
        "message": "Plot deleted"
    }


@router.get(
    "/{plot_id}",
    response_model=PlotResponse
)
def get_plot(
    farm_id: UUID,
    plot_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return plot_service.get_by_id(
        db,
        plot_id,
        current_user.id
    )

