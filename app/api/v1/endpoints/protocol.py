from fastapi import APIRouter, Depends

from app.api.v1.deps import DbSession, get_current_actor
from app.core.response import success
from app.schemas.protocol_context import ProtocolContextRequest
from app.services.community import get_agent_protocol_context
from app.services.protocol_manager import current_protocol_document

router = APIRouter()


@router.get("/current", response_model=dict)
async def get_current_protocol() -> dict:
    return success(current_protocol_document())


@router.post("/context", response_model=dict)
async def get_protocol_context(
    payload: ProtocolContextRequest,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    # Minimal runtime interface for agents to request scoped protocol context from community.
    return success(
        await get_agent_protocol_context(
            session,
            group_id=payload.group_id,
            actor=actor,
            action_type=payload.action_type,
            trigger=payload.trigger,
            resource_id=payload.resource_id,
            metadata=payload.metadata,
        )
    )
