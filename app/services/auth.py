from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_admin_access_token, hash_password, verify_password
from app.core.exceptions import AppError
from app.core.security import generate_agent_token, hash_token
from app.models.admin_user import AdminUser
from app.models.agent import Agent
from app.schemas.auth import AdminLoginRequest, AdminUserCreate


async def register_admin_user(session: AsyncSession, payload: AdminUserCreate) -> tuple[AdminUser, str]:
    existing = await session.scalar(select(AdminUser).where(AdminUser.username == payload.username))
    if existing:
        raise AppError("admin username already exists", code="admin_exists", status_code=409)

    bound_agent = Agent(
        name=f"human-{payload.username}",
        description=f"Bound agent for human admin {payload.display_name}",
        metadata_json={"kind": "human_admin"},
        is_moderator=True,
        token_hash=hash_token(generate_agent_token()),
    )
    session.add(bound_agent)
    await session.flush()

    admin_user = AdminUser(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        email=str(payload.email) if payload.email else None,
        is_superuser=True,
        is_active=True,
        bound_agent_id=bound_agent.id,
    )
    session.add(admin_user)
    await session.commit()
    await session.refresh(admin_user)
    return admin_user, create_admin_access_token(admin_user.id)


async def login_admin_user(session: AsyncSession, payload: AdminLoginRequest) -> tuple[AdminUser, str]:
    admin_user = await session.scalar(select(AdminUser).where(AdminUser.username == payload.username))
    if admin_user is None or not admin_user.is_active:
        raise AppError("invalid username or password", code="invalid_credentials", status_code=401)
    if not verify_password(payload.password, admin_user.password_hash):
        raise AppError("invalid username or password", code="invalid_credentials", status_code=401)
    await session.refresh(admin_user, attribute_names=["bound_agent"])
    return admin_user, create_admin_access_token(admin_user.id)
