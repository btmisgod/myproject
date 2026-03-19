from fastapi import APIRouter, Depends

from app.api.v1.deps import DbSession, get_current_admin_user
from app.core.response import success
from app.schemas.auth import AdminLoginRequest, AdminLoginResult, AdminUserCreate, AdminUserRead
from app.services.auth import login_admin_user, register_admin_user

router = APIRouter()


@router.post("/admin/register", response_model=dict)
async def register_admin(payload: AdminUserCreate, session: DbSession) -> dict:
    admin_user, access_token = await register_admin_user(session, payload)
    data = AdminLoginResult(
        access_token=access_token,
        admin_user=AdminUserRead.model_validate(admin_user),
    )
    return success(data.model_dump(), message="admin user registered")


@router.post("/admin/login", response_model=dict)
async def login_admin(payload: AdminLoginRequest, session: DbSession) -> dict:
    admin_user, access_token = await login_admin_user(session, payload)
    data = AdminLoginResult(
        access_token=access_token,
        admin_user=AdminUserRead.model_validate(admin_user),
    )
    return success(data.model_dump(), message="admin login ok")


@router.get("/admin/me", response_model=dict)
async def current_admin(admin_user=Depends(get_current_admin_user)) -> dict:
    return success(AdminUserRead.model_validate(admin_user).model_dump())
