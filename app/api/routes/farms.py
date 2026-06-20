from fastapi import APIRouter
from fastapi import Depends

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.dependencies import get_current_user

from app.models.user import User

from app.schemas.farm import FarmCreate
from app.schemas.farm import FarmResponse
from app.schemas.farm import FarmUpdate

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


@router.put(
    "/{farm_id}",
    response_model=FarmResponse
)
def update_farm(
    farm_id: UUID,
    farm_data: FarmUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return farm_service.update(
        db,
        farm_id,
        farm_data,
        current_user.id
    )


@router.delete(
    "/{farm_id}"
)
def delete_farm(
    farm_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    farm_service.delete(
        db,
        farm_id,
        current_user.id
    )

    return {
        "message": "Farm deleted"
    }