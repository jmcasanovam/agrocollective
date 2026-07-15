"""
Fase 3: Obtención de datos históricos y generación de variables agregadas.

Para cada parcela calcula los indicadores que alimentan el clustering (Fase 4):

  Fuente InfluxDB (ventana configurable, por defecto 30 días):
    - avg_soil_humidity   : humedad media del suelo (%)
    - avg_air_temp        : temperatura media del aire (°C)
    - avg_soil_temp       : temperatura media del suelo (°C)
    - avg_air_humidity    : humedad relativa media del aire (%)

  Fuente PostgreSQL (misma ventana):
    - irrigation_frequency : número de riegos en la ventana
    - avg_irrigation_mm    : media de mm por riego
    - total_water_mm       : mm totales aplicados en la ventana

  Fuente PostgreSQL (última cosecha disponible):
    - yield_kg_ha          : producción en kg/ha
    - water_efficiency     : kg/m³  (yield_kg_ha / total_water_mm * 100)
                             None si no hay cosecha o riego registrado
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.influx import Measurements, get_influx_client, get_query_api
from app.models.harvest import Harvest
from app.models.irrigation_record import IrrigationRecord
from app.models.plot import Plot

logger = logging.getLogger(__name__)


@dataclass
class PlotAggregates:
    """Variables agregadas de una parcela. None = dato no disponible."""
    plot_id: UUID
    hash_plot: str

    # Sensores (InfluxDB)
    avg_soil_humidity: float | None = None
    avg_air_temp: float | None = None
    avg_soil_temp: float | None = None
    avg_air_humidity: float | None = None

    # Riego (PostgreSQL)
    irrigation_frequency: int = 0
    avg_irrigation_mm: float | None = None
    total_water_mm: float | None = None

    # Cosecha (PostgreSQL)
    yield_kg_ha: float | None = None
    water_efficiency: float | None = None  # kg/m³


class AggregationService:

    def compute(self, db: Session, plot: Plot, window_days: int | None = None) -> PlotAggregates:
        """
        Calcula todas las variables agregadas para una parcela.

        Args:
            db: sesión PostgreSQL activa.
            plot: objeto Plot con hash_plot ya generado.
            window_days: días hacia atrás de la ventana. Si None, usa AGGREGATION_WINDOW_DAYS del .env.
        """
        days = window_days if window_days is not None else settings.AGGREGATION_WINDOW_DAYS
        aggregates = PlotAggregates(plot_id=plot.id, hash_plot=plot.hash_plot or "")

        if not plot.hash_plot:
            logger.warning("Parcela %s sin hash_plot. Omitida.", plot.id)
            return aggregates

        since = datetime.now(timezone.utc) - timedelta(days=days)

        self._fill_sensor_averages(aggregates, since)
        self._fill_irrigation(db, aggregates, plot.id, since)
        self._fill_yield(db, aggregates, plot.id)
        self._compute_efficiency(aggregates)

        logger.debug(
            "Agregados parcela %s | hum=%.1f air=%.1f riego=%d mm=%.1f yield=%s eff=%s",
            str(plot.id)[:8],
            aggregates.avg_soil_humidity or 0,
            aggregates.avg_air_temp or 0,
            aggregates.irrigation_frequency,
            aggregates.total_water_mm or 0,
            aggregates.yield_kg_ha,
            aggregates.water_efficiency,
        )
        return aggregates

    # -------------------------------------------------------------------------
    # InfluxDB: medias de sensores
    # -------------------------------------------------------------------------

    def _fill_sensor_averages(self, agg: PlotAggregates, since: datetime) -> None:
        """Consulta InfluxDB y rellena las medias de los campos de sensor."""
        since_rfc = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        flux = f"""
            from(bucket: "{settings.INFLUXDB_BUCKET_MEASUREMENTS}")
              |> range(start: {since_rfc})
              |> filter(fn: (r) => r._measurement == "{Measurements.SENSORS}")
              |> filter(fn: (r) => r.hash_plot == "{agg.hash_plot}")
              |> filter(fn: (r) =>
                    r._field == "soil_humidity" or
                    r._field == "air_temp"      or
                    r._field == "soil_temp"     or
                    r._field == "relative_humidity")
              |> mean()
        """
        try:
            client = get_influx_client()
            try:
                tables = get_query_api(client).query(flux, org=settings.INFLUXDB_ORG)
            finally:
                client.close()

            field_map = {
                "soil_humidity":    "avg_soil_humidity",
                "air_temp":         "avg_air_temp",
                "soil_temp":        "avg_soil_temp",
                "relative_humidity":"avg_air_humidity",
            }
            for table in tables:
                for record in table.records:
                    attr = field_map.get(record.get_field())
                    if attr:
                        setattr(agg, attr, record.get_value())

        except Exception as exc:
            logger.error("Error consultando InfluxDB para hash_plot=%s...: %s", agg.hash_plot[:8], exc)

    # -------------------------------------------------------------------------
    # PostgreSQL: registros de riego
    # -------------------------------------------------------------------------

    def _fill_irrigation(self, db: Session, agg: PlotAggregates, plot_id: UUID, since: datetime) -> None:
        """Calcula frecuencia, media y total de mm de riego en la ventana."""
        since_date = since.date()
        records: list[IrrigationRecord] = (
            db.query(IrrigationRecord)
            .filter(
                IrrigationRecord.plot_id == plot_id,
                IrrigationRecord.week_start >= since_date,
            )
            .all()
        )

        if not records:
            return

        mm_values = [r.irrigation_mm for r in records]
        agg.irrigation_frequency = len(mm_values)
        agg.total_water_mm = sum(mm_values)
        agg.avg_irrigation_mm = agg.total_water_mm / agg.irrigation_frequency

    # -------------------------------------------------------------------------
    # PostgreSQL: última cosecha
    # -------------------------------------------------------------------------

    def _fill_yield(self, db: Session, agg: PlotAggregates, plot_id: UUID) -> None:
        """Toma el yield_kg_ha de la cosecha más reciente de la parcela."""
        harvest: Harvest | None = (
            db.query(Harvest)
            .filter(Harvest.plot_id == plot_id)
            .order_by(Harvest.harvest_date.desc())
            .first()
        )
        if harvest and harvest.yield_kg_ha is not None:
            agg.yield_kg_ha = harvest.yield_kg_ha

    # -------------------------------------------------------------------------
    # Eficiencia hídrica
    # -------------------------------------------------------------------------

    def _compute_efficiency(self, agg: PlotAggregates) -> None:
        """
        Eficiencia hídrica = yield_kg_ha / (total_water_mm × 10) en kg/m³.
        (1 mm/ha = 10 m³/ha)
        None si falta yield o riego.
        """
        if agg.yield_kg_ha is not None and agg.total_water_mm and agg.total_water_mm > 0:
            water_m3_ha = agg.total_water_mm * 10
            agg.water_efficiency = round(agg.yield_kg_ha / water_m3_ha, 4)


aggregation_service = AggregationService()
