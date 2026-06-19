from uuid import UUID

from sqlalchemy.orm import Session

from app.models.farm import Farm
from app.schemas.farm import FarmCreate


class FarmRepository:


    def create(
        self,
        db: Session,
        farm_data: FarmCreate,
        user_id: UUID
    ) -> Farm:

        farm = Farm(
            user_id=user_id,
            name=farm_data.name,
            latitude=farm_data.latitude,
            longitude=farm_data.longitude,
            province=farm_data.province,
            area_ha=farm_data.area_ha
        )

        db.add(farm)
        db.commit()
        db.refresh(farm)

        return farm


    def get_by_id(
        self,
        db: Session,
        farm_id: UUID,
        user_id: UUID
    ) -> Farm | None:

        return (
            db.query(Farm)
            .filter(
                Farm.id == farm_id,
                Farm.user_id == user_id
            )
            .first()
        )


    def get_all_by_user(
        self,
        db: Session,
        user_id: UUID
    ) -> list[Farm]:

        return (
            db.query(Farm)
            .filter(
                Farm.user_id == user_id
            )
            .all()
        )


    def delete(
        self,
        db: Session,
        farm: Farm
    ):

        db.delete(farm)
        db.commit()


farm_repository = FarmRepository()