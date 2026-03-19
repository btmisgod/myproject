from typing import Annotated

from fastapi import Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import ActorContext, decode_access_token
from app.core.exceptions import AppError
from app.core.security import hash_token
from app.db.session import get_db_session
from app.models.agent import Agent
from app.models.admin_user import AdminUser


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_agent(
    session: DbSession,
    x_agent_token: Annotated[str | None, Header()] = None,
    agent_token: Annotated[str | None, Query(alias="agent_token")] = None,
) -> Agent:
    token = x_agent_token or agent_token
    if not token:
        raise AppError("missing X-Agent-Token header", code="auth_required", status_code=401)

    stmt = select(Agent).where(Agent.token_hash == hash_token(token), Agent.is_active.is_(True))
    agent = (await session.execute(stmt)).scalar_one_or_none()
    if agent is None:
        raise AppError("invalid agent token", code="invalid_token", status_code=401)
    return agent


async def get_current_admin_user(
    session: DbSession,
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Query(alias="access_token")] = None,
) -> AdminUser:
    bearer = authorization
    if not bearer and access_token:
        bearer = f"Bearer {access_token}"
    if not bearer or not bearer.startswith("Bearer "):
        raise AppError("missing bearer token", code="auth_required", status_code=401)

    token = bearer.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except Exception as exc:
        raise AppError("invalid bearer token", code="invalid_token", status_code=401) from exc

    if payload.get("kind") != "admin_user":
        raise AppError("invalid token kind", code="invalid_token", status_code=401)

    admin_user = await session.get(AdminUser, payload["sub"])
    if admin_user is None or not admin_user.is_active:
        raise AppError("admin user not found", code="admin_not_found", status_code=401)
    return admin_user


async def get_current_actor(
    session: DbSession,
    x_agent_token: Annotated[str | None, Header()] = None,
    agent_token: Annotated[str | None, Query(alias="agent_token")] = None,
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Query(alias="access_token")] = None,
) -> ActorContext:
    if x_agent_token or agent_token:
        agent = await get_current_agent(session, x_agent_token=x_agent_token, agent_token=agent_token)
        return ActorContext(actor_type="agent", agent=agent, admin_user=None)

    admin_user = await get_current_admin_user(
        session,
        authorization=authorization,
        access_token=access_token,
    )
    if admin_user.bound_agent_id is None:
        raise AppError("admin user has no bound agent", code="admin_agent_missing", status_code=500)
    bound_agent = await session.get(Agent, admin_user.bound_agent_id)
    if bound_agent is None:
        raise AppError("bound admin agent not found", code="admin_agent_missing", status_code=500)
    return ActorContext(actor_type="admin_user", agent=bound_agent, admin_user=admin_user)
