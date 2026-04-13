from fastapi import APIRouter, Depends

from app.api.v1.deps import DbSession, get_current_actor, get_current_agent
from app.core.response import success
from app.schemas.agents import AgentCreate, AgentProfileUpdateRequest, AgentRead, AgentRegistrationResult
from app.schemas.sessions import AgentSessionSyncRequest
from app.schemas.webhooks import AgentWebhookSubscriptionRead, WebhookSubscriptionCreate
from app.services.session_sync import sync_agent_session
from app.services.community import (
    create_agent_webhook_subscription,
    deactivate_agent_webhook_subscription,
    get_agent_webhook_subscription,
    register_agent,
    update_agent_profile,
)
from app.services.query import list_agents

router = APIRouter()


@router.post("", response_model=dict)
async def create_agent(payload: AgentCreate, session: DbSession) -> dict:
    agent, token = await register_agent(session, payload)
    data = AgentRegistrationResult(agent=AgentRead.model_validate(agent), token=token)
    return success(data.model_dump(), message="agent registered")


@router.get("", response_model=dict)
async def get_agents(session: DbSession, _=Depends(get_current_actor)) -> dict:
    agents = [AgentRead.model_validate(agent).model_dump() for agent in await list_agents(session)]
    return success(agents)


@router.get("/me", response_model=dict)
async def get_my_agent(agent=Depends(get_current_agent)) -> dict:
    return success(AgentRead.model_validate(agent).model_dump())


@router.patch("/me/profile", response_model=dict)
async def patch_my_agent_profile(
    payload: AgentProfileUpdateRequest,
    session: DbSession,
    agent=Depends(get_current_agent),
) -> dict:
    updated = await update_agent_profile(session, agent, payload)
    return success(AgentRead.model_validate(updated).model_dump(), message="agent profile updated")


@router.get("/me/webhook", response_model=dict)
async def get_my_agent_webhook(
    session: DbSession,
    agent=Depends(get_current_agent),
) -> dict:
    subscription = await get_agent_webhook_subscription(session, actor=agent)
    if subscription is None:
        return success(None)
    return success(AgentWebhookSubscriptionRead.model_validate(subscription).model_dump())


@router.post("/me/webhook", response_model=dict)
async def create_my_agent_webhook(
    payload: WebhookSubscriptionCreate,
    session: DbSession,
    agent=Depends(get_current_agent),
) -> dict:
    subscription = await create_agent_webhook_subscription(session, actor=agent, payload=payload)
    return success(AgentWebhookSubscriptionRead.model_validate(subscription).model_dump(), message="agent webhook registered")


@router.delete("/me/webhook", response_model=dict)
async def deactivate_my_agent_webhook(
    session: DbSession,
    agent=Depends(get_current_agent),
) -> dict:
    subscription = await deactivate_agent_webhook_subscription(session, actor=agent)
    return success(AgentWebhookSubscriptionRead.model_validate(subscription).model_dump(), message="agent webhook deactivated")


@router.post("/me/session/sync", response_model=dict)
async def sync_my_agent_session(
    payload: AgentSessionSyncRequest,
    session: DbSession,
    agent=Depends(get_current_agent),
) -> dict:
    data = await sync_agent_session(session, agent=agent, payload=payload)
    return success(data, message="agent session synced")
