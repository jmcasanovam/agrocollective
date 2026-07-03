from uuid import UUID

from sqlalchemy.orm import Session

from app.models.harvest import Harvest
from app.schemas.harvest import HarvestCreate


class HarvestRepository:

    def create(self, db: Session, plot_id: UUID, data: HarvestCreate) -> Harvest:
        harvest = Harvest(
            plot_id=plot_id,
            harvest_date=data.harvest_date,
            yield_kg_ha=data.yield_kg_ha,
            water_consumed_m3_ha=data.water_consumed_m3_ha,
        )
        db.add(harvest)
        db.commit()
        db.refresh(harvest)
        return harvest

    def get_all_by_plot(self, db: Session, plot_id: UUID) -> list[Harvest]:
        return (
            db.query(Harvest)
            .filter(Harvest.plot_id == plot_id)
            .order_by(Harvest.harvest_date.desc())
            .all()
        )


harvest_repository = HarvestRepository()
