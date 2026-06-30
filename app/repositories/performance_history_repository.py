from datetime import date

from sqlalchemy.orm import Session

from app.models.plot_performance_history import PlotPerformanceHistory
from app.services.history.performance_history_service import PerformanceSnapshot


class PerformanceHistoryRepository:

    def save_snapshots(self, db: Session, snapshots: list[PerformanceSnapshot]) -> None:
        """Upsert por (plot_id, run_date): elimina el registro del día y lo recrea."""
        if not snapshots:
            return

        run_date = snapshots[0].run_date
        db.query(PlotPerformanceHistory).filter(
            PlotPerformanceHistory.run_date == run_date
        ).delete()

        for s in snapshots:
            db.add(PlotPerformanceHistory(
                plot_id=s.plot_id,
                run_date=s.run_date,
                cluster_id=s.cluster_id,
                avg_soil_humidity=s.avg_soil_humidity,
                avg_air_temp=s.avg_air_temp,
                avg_soil_temp=s.avg_soil_temp,
                avg_air_humidity=s.avg_air_humidity,
                irrigation_frequency=s.irrigation_frequency,
                avg_irrigation_mm=s.avg_irrigation_mm,
                total_water_mm=s.total_water_mm,
                yield_kg_ha=s.yield_kg_ha,
                water_efficiency=s.water_efficiency,
                is_anomaly=s.is_anomaly,
                lof_score=s.lof_score,
                predicted_yield=s.predicted_yield,
                predicted_efficiency=s.predicted_efficiency,
                n_recommendations=s.n_recommendations,
                n_high_priority=s.n_high_priority,
            ))

        db.commit()

    def get_history_for_plot(
        self, db: Session, plot_id, limit: int = 90
    ) -> list[PlotPerformanceHistory]:
        """Devuelve los últimos `limit` registros de una parcela, del más reciente al más antiguo."""
        return (
            db.query(PlotPerformanceHistory)
            .filter(PlotPerformanceHistory.plot_id == plot_id)
            .order_by(PlotPerformanceHistory.run_date.desc())
            .limit(limit)
            .all()
        )

    def get_snapshot(
        self, db: Session, plot_id, run_date: date
    ) -> PlotPerformanceHistory | None:
        return (
            db.query(PlotPerformanceHistory)
            .filter(
                PlotPerformanceHistory.plot_id == plot_id,
                PlotPerformanceHistory.run_date == run_date,
            )
            .first()
        )


performance_history_repository = PerformanceHistoryRepository()
