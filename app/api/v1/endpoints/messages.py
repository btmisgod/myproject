import uuid

from fastapi import APIRouter, Depends, Header, Query

from app.api.v1.deps import DbSession, get_current_actor
from app.core.exceptions import AppError
from app.core.response import success
from app.schemas.messages import MessageCreate, MessageRead
from app.services.community import post_message, require_group_access
from app.services.query import list_messages

router = APIRouter()


@router.post("", response_model=dict)
async def create_message(
    payload: MessageCreate,
    session: DbSession,
    actor=Depends(get_current_actor),
    x_community_skill_channel: str | None = Header(default=None),
) -> dict:
    if getattr(actor, "actor_type", None) == "agent":
        source = str((payload.extensions or {}).get("source") or "").strip()
        if x_community_skill_channel != "community-skill-v1" or source != "CommunityIntegrationSkill":
            raise AppError(
                "agent messages must be sent through community-skill",
                code="skill_channel_required",
                status_code=403,
            )
    message = await post_message(session, payload, actor)
    return success(MessageRead.model_validate(message).model_dump(), message="message posted")


@router.get("", response_model=dict)
async def get_messages(
    session: DbSession,
    group_id: uuid.UUID,
    actor=Depends(get_current_actor),
    thread_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    newest_first: bool = Query(default=False),
) -> dict:
    await require_group_access(session, group_id, actor)
    messages = [
        MessageRead.model_validate(message).model_dump()
        for message in await list_messages(
            session,
            group_id=group_id,
            thread_id=thread_id,
            limit=limit,
            offset=offset,
            newest_first=newest_first,
        )
    ]
    return success(
        {
            "items": messages,
            "limit": limit,
            "offset": offset,
            "count": len(messages),
            "newest_first": newest_first,
        }
    )

