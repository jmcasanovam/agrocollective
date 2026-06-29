from datetime import date

from sqlalchemy.orm import Session

from app.models.plot_anomaly import PlotAnomaly
from app.services.anomalies.lof_service import AnomalyResult


class AnomalyRepository:

    def save_results(self, db: Session, results: list[AnomalyResult]) -> None:
        """Reemplaza las anomalías del run_date con las nuevas (idempotente)."""
        if not results:
            return

        run_date = results[0].run_date
        db.query(PlotAnomaly).filter(PlotAnomaly.run_date == run_date).delete()

        for r in results:
            db.add(PlotAnomaly(
                plot_id=r.plot_id,
                run_date=r.run_date,
                cluster_id=r.cluster_id,
                lof_score=r.lof_score,
                is_anomaly=r.is_anomaly,
                anomalous_features=",".join(r.anomalous_features) if r.anomalous_features else None,
            ))

        db.commit()

    def get_anomalies_by_date(self, db: Session, run_date: date) -> list[PlotAnomaly]:
        return (
            db.query(PlotAnomaly)
            .filter(PlotAnomaly.run_date == run_date, PlotAnomaly.is_anomaly == True)
            .all()
        )


anomaly_repository = AnomalyRepository()
