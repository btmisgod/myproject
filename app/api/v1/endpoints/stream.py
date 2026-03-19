import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from app.api.v1.deps import DbSession, get_current_actor
from app.services.community import require_group_access
from app.services.event_bus import stream_group_events

router = APIRouter()


@router.get("/groups/{group_id}")
async def group_stream(
    group_id: uuid.UUID,
    session: DbSession,
    actor=Depends(get_current_actor),
    heartbeat: int = Query(default=15, ge=5, le=60),
):
    await require_group_access(session, group_id, actor)

    async def event_generator():
        while True:
            try:
                async for event in stream_group_events(group_id):
                    yield {"event": "group_event", "data": json.dumps(event)}
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                yield {"event": "error", "data": json.dumps({"message": str(exc)})}
                await asyncio.sleep(heartbeat)

    return EventSourceResponse(event_generator())
