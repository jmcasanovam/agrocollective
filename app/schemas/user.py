from uuid import UUID

from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import ConfigDict


class UserBase(BaseModel):
    email: EmailStr
    region: str | None = None


class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: UUID
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"