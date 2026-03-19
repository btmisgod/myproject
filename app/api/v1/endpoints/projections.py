import uuid

from fastapi import APIRouter, Depends

from app.api.v1.deps import DbSession, get_current_actor
from app.core.response import success
from app.schemas.agents import AgentRead
from app.schemas.common import EventEnvelope
from app.schemas.groups import GroupRead
from app.schemas.messages import MessageRead
from app.schemas.presence import PresenceRead
from app.schemas.projection import GroupProjectionSnapshot
from app.schemas.tasks import TaskRead
from app.services.community import get_group_or_404, require_group_access
from app.services.query import (
    latest_host_summary,
    list_events,
    list_group_agents,
    list_messages,
    list_presence,
    list_tasks,
)

router = APIRouter()


@router.get("/groups/{group_id}/snapshot", response_model=dict)
async def get_group_snapshot(group_id: uuid.UUID, session: DbSession, actor=Depends(get_current_actor)) -> dict:
    await require_group_access(session, group_id, actor)
    group = await get_group_or_404(session, group_id)
    members = [AgentRead.model_validate(item) for item in await list_group_agents(session, group_id)]
    presence = [PresenceRead.model_validate(item) for item in await list_presence(session, group_id=group_id)]
    tasks = [TaskRead.model_validate(item) for item in await list_tasks(session, group_id=group_id)]
    latest_messages = await list_messages(session, group_id=group_id, limit=25, offset=0, newest_first=True)
    messages = [MessageRead.model_validate(item) for item in reversed(latest_messages)]
    events = [EventEnvelope.model_validate(item) for item in await list_events(session, group_id=group_id)]
    snapshot = GroupProjectionSnapshot(
        group=GroupRead.model_validate(group),
        members=members,
        online_members=presence,
        tasks=tasks,
        latest_messages=messages,
        latest_events=events,
        host_summary=await latest_host_summary(session, group_id=group_id),
        replay_cursor=events[-1].sequence_id if events else None,
    )
    return success(snapshot.model_dump())
