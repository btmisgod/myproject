import uuid

from fastapi import APIRouter, Depends

from app.api.v1.deps import DbSession, get_current_actor
from app.core.response import success
from app.schemas.common import EventEnvelope
from app.schemas.groups import GroupCreate, JoinGroupRequest, MembershipRead
from app.schemas.protocols import GroupProtocolUpdateRequest
from app.schemas.webhooks import WebhookSubscriptionCreate, WebhookSubscriptionRead
from app.services.community import (
    create_group,
    create_webhook_subscription,
    deactivate_webhook_subscription,
    get_group_by_slug_or_404,
    get_group_context,
    get_group_session,
    get_group_protocol,
    join_group,
    require_group_access,
    update_group_protocol,
)
from app.services.query import list_events, list_group_memberships, list_groups, list_webhook_subscriptions

router = APIRouter()


def _serialize_group_read(group) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "slug": group.slug,
        "description": group.description,
        "group_type": group.group_type,
        "metadata_json": group.metadata_json,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }


@router.post("", response_model=dict)
async def create_group_endpoint(
    payload: GroupCreate,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    group = await create_group(session, payload, actor.agent)
    return success(_serialize_group_read(group), message="group created")


@router.get("", response_model=dict)
async def get_groups(session: DbSession, _=Depends(get_current_actor)) -> dict:
    groups = [_serialize_group_read(group) for group in await list_groups(session)]
    return success(groups)


@router.get("/by-slug/{slug}", response_model=dict)
async def get_group_by_slug(
    slug: str,
    session: DbSession,
    _=Depends(get_current_actor),
) -> dict:
    group = await get_group_by_slug_or_404(session, slug)
    return success(_serialize_group_read(group))


@router.post("/{group_id}/join", response_model=dict)
async def join_group_endpoint(
    group_id: uuid.UUID,
    payload: JoinGroupRequest,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    _ = payload
    membership = await join_group(session, group_id, actor.agent)
    return success(MembershipRead.model_validate(membership).model_dump(), message="joined group")


@router.post("/by-slug/{slug}/join", response_model=dict)
async def join_group_by_slug_endpoint(
    slug: str,
    payload: JoinGroupRequest,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    group = await get_group_by_slug_or_404(session, slug)
    _ = payload
    membership = await join_group(session, group.id, actor.agent)
    group = await get_group_by_slug_or_404(session, slug)
    return success(
        {
            "group": _serialize_group_read(group),
            "membership": MembershipRead.model_validate(membership).model_dump(),
        },
        message="joined group",
    )


@router.get("/{group_id}/protocol", response_model=dict)
async def get_group_protocol_endpoint(
    group_id: uuid.UUID,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    data = await get_group_protocol(session, group_id, actor)
    return success(data)


@router.get("/by-slug/{slug}/protocol", response_model=dict)
async def get_group_protocol_by_slug_endpoint(
    slug: str,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    group = await get_group_by_slug_or_404(session, slug)
    data = await get_group_protocol(session, group.id, actor)
    return success(data)


@router.get("/{group_id}/context", response_model=dict)
async def get_group_context_endpoint(
    group_id: uuid.UUID,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    return success(await get_group_context(session, group_id, actor))


@router.get("/{group_id}/session", response_model=dict)
async def get_group_session_endpoint(
    group_id: uuid.UUID,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    return success(await get_group_session(session, group_id, actor))


# Deprecated compatibility alias only. Formal server semantics use
# /groups/{group_id}/context and group_* naming.
@router.get("/{group_id}/channel-context", response_model=dict)
async def get_group_channel_context_legacy_endpoint(
    group_id: uuid.UUID,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    return success(await get_group_context(session, group_id, actor))


@router.get("/by-slug/{slug}/context", response_model=dict)
async def get_group_context_by_slug_endpoint(
    slug: str,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    group = await get_group_by_slug_or_404(session, slug)
    return success(await get_group_context(session, group.id, actor))


@router.get("/by-slug/{slug}/session", response_model=dict)
async def get_group_session_by_slug_endpoint(
    slug: str,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    group = await get_group_by_slug_or_404(session, slug)
    return success(await get_group_session(session, group.id, actor))


# Deprecated compatibility alias only. Formal server semantics use
# /groups/by-slug/{slug}/context and group_* naming.
@router.get("/by-slug/{slug}/channel-context", response_model=dict)
async def get_group_channel_context_by_slug_legacy_endpoint(
    slug: str,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    group = await get_group_by_slug_or_404(session, slug)
    return success(await get_group_context(session, group.id, actor))


@router.patch("/{group_id}/protocol", response_model=dict)
async def patch_group_protocol_endpoint(
    group_id: uuid.UUID,
    payload: GroupProtocolUpdateRequest,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    group = await update_group_protocol(
        session,
        group_id=group_id,
        actor=actor,
        group_protocol=payload.group_protocol,
    )
    return success(_serialize_group_read(group), message="group protocol updated")


@router.get("/{group_id}/members", response_model=dict)
async def get_group_members(
    group_id: uuid.UUID,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    await require_group_access(session, group_id, actor)
    memberships = [
        MembershipRead.model_validate(item).model_dump()
        for item in await list_group_memberships(session, group_id)
    ]
    return success(memberships)


@router.get("/{group_id}/events", response_model=dict)
async def get_group_events(
    group_id: uuid.UUID,
    session: DbSession,
    actor=Depends(get_current_actor),
    after_sequence: int | None = None,
    limit: int = 100,
) -> dict:
    await require_group_access(session, group_id, actor)
    events = [
        EventEnvelope.model_validate(event).model_dump()
        for event in await list_events(session, group_id=group_id, after_sequence=after_sequence, limit=limit)
    ]
    return success({"items": events, "after_sequence": after_sequence, "limit": limit, "count": len(events)})


@router.get("/{group_id}/webhooks", response_model=dict)
async def get_group_webhooks(
    group_id: uuid.UUID,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    await require_group_access(session, group_id, actor)
    items = [
        WebhookSubscriptionRead.model_validate(item).model_dump()
        for item in await list_webhook_subscriptions(session, group_id=group_id)
    ]
    return success(items)


@router.post("/{group_id}/webhooks", response_model=dict)
async def create_group_webhook(
    group_id: uuid.UUID,
    payload: WebhookSubscriptionCreate,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    item = await create_webhook_subscription(session, group_id=group_id, actor=actor, payload=payload)
    return success(WebhookSubscriptionRead.model_validate(item).model_dump(), message="webhook registered")


@router.delete("/{group_id}/webhooks/{webhook_id}", response_model=dict)
async def deactivate_group_webhook(
    group_id: uuid.UUID,
    webhook_id: uuid.UUID,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    item = await deactivate_webhook_subscription(
        session,
        group_id=group_id,
        webhook_id=webhook_id,
        actor=actor,
    )
    return success(WebhookSubscriptionRead.model_validate(item).model_dump(), message="webhook deactivated")
