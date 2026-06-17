from datetime import UTC
from datetime import datetime

from fastapi import Depends
from fastapi import FastAPI

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_db


app = FastAPI(
    title="AgroCollective API",
    version="0.1.0"
)


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