"""
Cliente InfluxDB y constantes de esquema v2.1.

Mediciones de CLIMA (SiAR):
  weather        : grano DIARIO (DatosCalculados=true). Sin weather_daily.
  weather_weekly : downsampling semanal desde weather (task InfluxDB).
                   Mismos límites de semana que measurements_weekly.

Mediciones de SENSORES (IoT):
  measurements         : grano HORARIO
  measurements_daily   : downsampling diario (task InfluxDB)
  measurements_weekly  : downsampling semanal (task InfluxDB)
"""

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from app.core.config import settings


class Measurements:
    WEATHER          = "weather"
    WEATHER_WEEKLY   = "weather_weekly"
    SENSORS          = "measurements"
    SENSORS_DAILY    = "measurements_daily"
    SENSORS_WEEKLY   = "measurements_weekly"


# Tags y fields de referencia, usados por el simulador y los consumers

WEATHER_TAGS   = ["region_code", "siar_station_code"]
WEATHER_FIELDS = ["eto", "pe", "precipitation", "air_temp", "relative_humidity", "soil_temp"]
# eto  <- EtPMon  (mm/día, campo clave)
# pe   <- PePMon  (mm/día)

SENSOR_TAGS    = ["hash_plot", "region_code"]
SENSOR_FIELDS  = ["soil_humidity", "soil_temp", "air_temp", "relative_humidity", "battery"]


def get_influx_client() -> InfluxDBClient:
    return InfluxDBClient(
        url=f"http://{settings.INFLUXDB_HOST}:{settings.INFLUXDB_PORT}",
        token=settings.INFLUXDB_TOKEN,
        org=settings.INFLUXDB_ORG,
    )


def get_write_api(client: InfluxDBClient):
    return client.write_api(write_options=SYNCHRONOUS)


def get_query_api(client: InfluxDBClient):
    return client.query_api()
