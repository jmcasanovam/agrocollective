from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):

    # Aplicación
    APP_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # PostgreSQL
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # InfluxDB
    INFLUXDB_HOST: str
    INFLUXDB_PORT: int
    INFLUXDB_TOKEN: str
    INFLUXDB_ORG: str
    INFLUXDB_BUCKET: str

    # MQTT
    MQTT_HOST: str
    MQTT_PORT: int

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # SiAR (solo requerido por scripts/download_siar.py)
    SIAR_TOKEN: str = ""

    # Procesamiento inteligente
    AGGREGATION_WINDOW_DAYS: int = 30
    CLUSTERING_SCHEDULE_HOUR: int = 2
    KMEANS_MAX_CLUSTERS: int = 5
    LOF_N_NEIGHBORS: int = 5
    LOF_THRESHOLD: float = 1.5
    CAUSAL_MIN_PERIODS: int = 4
    CAUSAL_MIN_CORR: float = 0.6
    ANALOGUE_TOP_N: int = 5
    ML_MIN_SAMPLES: int = 10
    ML_N_ESTIMATORS: int = 100

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        case_sensitive=True
    )

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+psycopg2://"
            f"{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()