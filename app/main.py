from datetime import UTC
from datetime import datetime

from fastapi import FastAPI
from fastapi import Depends

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_db

from app.api.routes.auth import router as auth_router
from app.api.routes.farms import router as farms_router


app = FastAPI(
    title="AgroCollective API",
    version="0.1.0"
)


app.include_router(auth_router)
app.include_router(farms_router)

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