import uuid

from fastapi import APIRouter, Depends

from app.api.v1.deps import DbSession, get_current_actor
from app.core.response import success
from app.schemas.presence import PresenceRead, PresenceUpdateRequest
from app.services.community import require_group_access, update_presence
from app.services.query import list_presence

router = APIRouter()


@router.post("", response_model=dict)
async def update_presence_endpoint(
    payload: PresenceUpdateRequest,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    presence = await update_presence(session, actor, payload)
    return success(PresenceRead.model_validate(presence).model_dump(), message="presence updated")


@router.get("", response_model=dict)
async def get_presence(group_id: uuid.UUID, session: DbSession, actor=Depends(get_current_actor)) -> dict:
    await require_group_access(session, group_id, actor)
    presence = [
        PresenceRead.model_validate(item).model_dump()
        for item in await list_presence(session, group_id=group_id)
    ]
    return success(presence)
