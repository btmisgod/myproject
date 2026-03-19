import uuid

from fastapi import APIRouter, Depends

from app.api.v1.deps import DbSession, get_current_actor
from app.core.response import success
from app.schemas.tasks import (
    TaskClaimRequest,
    TaskCreate,
    TaskHandoffRequest,
    TaskRead,
    TaskResultSummaryRequest,
    TaskStatusUpdateRequest,
)
from app.services.community import (
    claim_task,
    create_task,
    handoff_task,
    require_group_access,
    save_task_result,
    update_task_status,
)
from app.services.query import list_tasks

router = APIRouter()


@router.post("", response_model=dict)
async def create_task_endpoint(
    payload: TaskCreate,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    task = await create_task(session, payload, actor)
    return success(TaskRead.model_validate(task).model_dump(), message="task created")


@router.get("", response_model=dict)
async def get_tasks(group_id: uuid.UUID, session: DbSession, actor=Depends(get_current_actor)) -> dict:
    await require_group_access(session, group_id, actor)
    tasks = [TaskRead.model_validate(task).model_dump() for task in await list_tasks(session, group_id=group_id)]
    return success(tasks)


@router.post("/{task_id}/claim", response_model=dict)
async def claim_task_endpoint(
    task_id: uuid.UUID,
    payload: TaskClaimRequest,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    task = await claim_task(session, task_id, actor, payload)
    return success(TaskRead.model_validate(task).model_dump(), message="task claimed")


@router.post("/{task_id}/status", response_model=dict)
async def update_task_status_endpoint(
    task_id: uuid.UUID,
    payload: TaskStatusUpdateRequest,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    task = await update_task_status(session, task_id, actor, payload)
    return success(TaskRead.model_validate(task).model_dump(), message="task updated")


@router.post("/{task_id}/handoff", response_model=dict)
async def handoff_task_endpoint(
    task_id: uuid.UUID,
    payload: TaskHandoffRequest,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    task = await handoff_task(session, task_id, actor, payload)
    return success(TaskRead.model_validate(task).model_dump(), message="task handed off")


@router.post("/{task_id}/result-summary", response_model=dict)
async def task_result_summary_endpoint(
    task_id: uuid.UUID,
    payload: TaskResultSummaryRequest,
    session: DbSession,
    actor=Depends(get_current_actor),
) -> dict:
    task = await save_task_result(session, task_id, actor, payload)
    return success(TaskRead.model_validate(task).model_dump(), message="task result saved")
