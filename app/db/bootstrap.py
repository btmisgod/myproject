import app.models  # noqa: F401
from app.db.session import engine
from app.models.base import Base


async def bootstrap_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
