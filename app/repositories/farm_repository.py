from uuid import UUID

from sqlalchemy.orm import Session

from app.models.farm import Farm
from app.schemas.farm import FarmCreate
from app.schemas.farm import FarmUpdate


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
                Farm.user_id == user_id,
                Farm.is_active.is_(True)
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
                Farm.user_id == user_id,
                Farm.is_active.is_(True)
            )
            .all()
        )


    def update(
        self,
        db: Session,
        farm: Farm,
        farm_data: FarmUpdate
    ) -> Farm:

        if farm_data.name is not None:
            farm.name = farm_data.name

        if farm_data.latitude is not None:
            farm.latitude = farm_data.latitude

        if farm_data.longitude is not None:
            farm.longitude = farm_data.longitude

        if farm_data.province is not None:
            farm.province = farm_data.province

        if farm_data.area_ha is not None:
            farm.area_ha = farm_data.area_ha

        db.commit()
        db.refresh(farm)

        return farm


    def delete(
        self,
        db: Session,
        farm: Farm
    ):

        farm.is_active = False
        db.commit()


farm_repository = FarmRepository()