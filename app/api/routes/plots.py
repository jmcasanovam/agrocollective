from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.dependencies import get_current_user

from app.models.user import User

from app.schemas.plot import PlotCreate
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
    farm_id: str,
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
    farm_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return plot_service.get_all(
        db,
        farm_id,
        current_user.id
    )