from uuid import UUID

from sqlalchemy.orm import Session

from app.models.irrigation_record import IrrigationRecord
from app.schemas.irrigation import IrrigationCreate


class IrrigationRepository:

    def create(self, db: Session, plot_id: UUID, data: IrrigationCreate) -> IrrigationRecord:
        record = IrrigationRecord(
            plot_id=plot_id,
            week_start=data.week_start,
            irrigation_mm=data.irrigation_mm,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_all_by_plot(self, db: Session, plot_id: UUID) -> list[IrrigationRecord]:
        return (
            db.query(IrrigationRecord)
            .filter(IrrigationRecord.plot_id == plot_id)
            .order_by(IrrigationRecord.week_start.desc())
            .all()
        )

    def get_by_plot_and_week(self, db: Session, plot_id: UUID, week_start) -> IrrigationRecord | None:
        return (
            db.query(IrrigationRecord)
            .filter(IrrigationRecord.plot_id == plot_id, IrrigationRecord.week_start == week_start)
            .first()
        )


irrigation_repository = IrrigationRepository()
