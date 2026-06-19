from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.dependencies import get_current_user

from app.models.user import User

from app.schemas.farm import FarmCreate
from app.schemas.farm import FarmResponse

from app.services.farms.farm_service import farm_service


router = APIRouter(
    prefix="/farms",
    tags=["Farms"]
)


@router.post(
    "",
    response_model=FarmResponse
)
def create_farm(
    farm_data: FarmCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return farm_service.create(
        db,
        farm_data,
        current_user.id
    )


@router.get(
    "",
    response_model=list[FarmResponse]
)
def get_my_farms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return farm_service.get_all(
        db,
        current_user.id
    )