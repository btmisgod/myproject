from fastapi import APIRouter

from app.core.response import success

router = APIRouter()


@router.get("/health")
async def healthcheck() -> dict:
    return success({"status": "ok"})

