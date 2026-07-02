"""
Fase 2: Ingesta y almacenamiento de lecturas IoT.

Flujo:
  1. Recibe el payload validado y el dispositivo identificado (Fase 1).
  2. Carga el contexto de la parcela (plot → farm → region).
  3. Usa hash_plot (ya generado en PostgreSQL) como tag de anonimización en InfluxDB.
  4. Actualiza last_seen_at y battery_mv en PostgreSQL (siempre, incluso si InfluxDB falla).
  5. Escribe el punto en InfluxDB.
"""

import logging
from datetime import datetime, timezone

from influxdb_client import Point
from sqlalchemy.orm import Session, joinedload

from app.database.influx import Measurements, get_influx_client, get_write_api
from app.models.device import Device
from app.models.plot import Plot
from app.models.farm import Farm

logger = logging.getLogger(__name__)


def store_reading(db: Session, device: Device, timestamp: datetime, battery_mv: int, measures: dict) -> None:
    """
    Persiste una lectura en InfluxDB y actualiza los metadatos del dispositivo en PostgreSQL.
    La actualización de PostgreSQL se realiza siempre, aunque InfluxDB falle.
    """
    plot, region_code = _load_plot_context(db, device)

    # Actualizar metadatos en PostgreSQL primero (operación más crítica y ligera)
    _update_device_metadata(db, device, timestamp, battery_mv)

    if plot.hash_plot is None:
        logger.error("La parcela %s no tiene hash_plot. Lectura no almacenada en InfluxDB.", plot.id)
        return

    # Escribir en InfluxDB de forma independiente para no bloquear la actualización de PG
    try:
        _write_to_influx(plot.hash_plot, region_code, timestamp, battery_mv, measures)
        logger.info(
            "Lectura almacenada | hash_plot=%s... | region=%s | campos=%s",
            plot.hash_plot[:8], region_code, list(measures.keys())
        )
    except Exception as exc:
        logger.error(
            "Error al escribir en InfluxDB para hash_plot=%s...: %s",
            plot.hash_plot[:8], exc
        )


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _load_plot_context(db: Session, device: Device) -> tuple[Plot, str]:
    """Carga la parcela con su finca y región en una sola query."""
    plot = (
        db.query(Plot)
        .options(joinedload(Plot.farm).joinedload(Farm.region))
        .filter(Plot.id == device.plot_id)
        .one()
    )
    region_code = plot.farm.region.code if (plot.farm and plot.farm.region) else "unknown"
    return plot, region_code


def _write_to_influx(
    hash_plot: str,
    region_code: str,
    timestamp: datetime,
    battery_mv: int,
    measures: dict,
) -> None:
    """Construye y escribe el punto en InfluxDB."""
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    point = (
        Point(Measurements.SENSORS)
        .tag("hash_plot", hash_plot)
        .tag("region_code", region_code)
        .time(timestamp)
        .field("battery", float(battery_mv))
    )

    field_map = {
        "soil_humidity": "soil_humidity",
        "air_temp":      "air_temp",
        "soil_temp":     "soil_temp",
        "air_humidity":  "relative_humidity",
    }
    for payload_key, influx_field in field_map.items():
        value = measures.get(payload_key)
        if value is not None:
            point = point.field(influx_field, float(value))

    from app.core.config import settings
    client = get_influx_client()
    try:
        write_api = get_write_api(client)
        write_api.write(bucket=settings.INFLUXDB_BUCKET_MEASUREMENTS, record=point)
    finally:
        client.close()


def _update_device_metadata(db: Session, device: Device, timestamp: datetime, battery_mv: int) -> None:
    """Actualiza los metadatos operativos del dispositivo en PostgreSQL."""
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    device.last_seen_at = timestamp
    device.battery_mv = battery_mv
    db.commit()
