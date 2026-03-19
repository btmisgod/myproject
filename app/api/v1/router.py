from fastapi import APIRouter

from app.api.v1.endpoints import agents, auth, groups, health, messages, presence, projections, protocol, stream, tasks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(protocol.router, prefix="/protocol", tags=["protocol"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(presence.router, prefix="/presence", tags=["presence"])
api_router.include_router(stream.router, prefix="/stream", tags=["stream"])
api_router.include_router(projections.router, prefix="/projection", tags=["projection"])
