# app/main.py
from datetime import datetime, UTC
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.dependencies import get_db
from app.schemas.user import UserCreate, UserRead
from app.services.auth.auth_service import UserService

app = FastAPI(
    title="AgroCollective API",
    version="0.1.0"
)

user_service = UserService()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat()
    }

@app.get("/health/db")
async def database_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "connected"}

@app.post("/users", response_model=UserRead)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db)
):
    return user_service.create_user(db, data)

@app.get("/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    return user_service.list_users(db) 
