from uuid import UUID
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    region: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: UUID

    class Config:
        from_attributes = True
