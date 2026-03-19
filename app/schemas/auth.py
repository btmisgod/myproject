import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = None


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminUserRead(ORMModel):
    id: uuid.UUID
    username: str
    display_name: str
    email: str | None
    is_superuser: bool
    is_active: bool
    bound_agent_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class AdminLoginResult(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_user: AdminUserRead
