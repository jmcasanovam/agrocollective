import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.workers import mqtt_consumer

from app.api.routes.auth import router as auth_router
from app.api.routes.farms import router as farms_router
from app.api.routes.plots import router as plots_router
from app.api.routes.devices import router as devices_router
from app.api.routes.sensors import router as sensors_router
from app.api.routes.catalog import router as catalog_router
from app.api.routes.intelligence import router as intelligence_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Arrancando MQTT consumer...")
    mqtt_consumer.start()
    yield
    logger.info("Apagando MQTT consumer...")
    mqtt_consumer.stop()


app = FastAPI(
    title="AgroCollective API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(farms_router)
app.include_router(plots_router)
app.include_router(devices_router)
app.include_router(sensors_router)
app.include_router(catalog_router)
app.include_router(intelligence_router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat()
    }


@app.get("/health/db")
async def database_health(
    db: Session = Depends(get_db)
):
    db.execute(text("SELECT 1"))
    return {
        "database": "connected"
    }
