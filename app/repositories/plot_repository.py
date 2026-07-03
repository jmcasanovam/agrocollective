import hashlib
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.plot import Plot
from app.models.farm import Farm
from app.models.user import User
from app.schemas.plot import PlotCreate, PlotUpdate


class PlotRepository:

    def create(self, db: Session, plot_data: PlotCreate, farm_id: UUID) -> Plot:
        plot = Plot(
            farm_id=farm_id,
            crop_id=plot_data.crop_id,
            soil_id=plot_data.soil_id,
            name=plot_data.name,
            area_ha=plot_data.area_ha,
            management_profile=plot_data.management_profile,
        )
        db.add(plot)
        db.commit()
        db.refresh(plot)

        plot.hash_plot = hashlib.sha256(str(plot.id).encode()).hexdigest()
        db.commit()
        db.refresh(plot)

        return plot

    def get_all_by_farm(self, db: Session, farm_id: UUID) -> list[Plot]:
        return db.query(Plot).filter(Plot.farm_id == farm_id).all()

    def get_by_farm_and_name(self, db: Session, farm_id: UUID, name: str) -> Plot | None:
        return db.query(Plot).filter(Plot.farm_id == farm_id, Plot.name == name).first()

    def get_by_id(self, db: Session, plot_id: UUID) -> Plot | None:
        return db.query(Plot).filter(Plot.id == plot_id).first()

    def get_by_id_and_user(self, db: Session, plot_id: UUID, user_id: UUID) -> Plot | None:
        return (
            db.query(Plot)
            .join(Farm, Farm.id == Plot.farm_id)
            .join(User, User.id == Farm.user_id)
            .filter(Plot.id == plot_id, Farm.user_id == user_id, User.is_active == True)
            .first()
        )

    def update(self, db: Session, plot: Plot, plot_data: PlotUpdate) -> Plot:
        if plot_data.crop_id is not None:
            plot.crop_id = plot_data.crop_id
        if plot_data.soil_id is not None:
            plot.soil_id = plot_data.soil_id
        if plot_data.name is not None:
            plot.name = plot_data.name
        if plot_data.area_ha is not None:
            plot.area_ha = plot_data.area_ha
        if plot_data.management_profile is not None:
            plot.management_profile = plot_data.management_profile
        db.commit()
        db.refresh(plot)
        return plot

    def delete(self, db: Session, plot: Plot) -> None:
        db.delete(plot)
        db.commit()


plot_repository = PlotRepository()
