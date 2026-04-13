from sqlalchemy import inspect

import app.models  # noqa: F401
from app.db.session import engine
from app.models.base import Base


def _ensure_message_contract_columns(sync_conn) -> None:
    inspector = inspect(sync_conn)
    if "messages" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("messages")}
    dialect = sync_conn.dialect.name
    json_type = "JSONB" if dialect == "postgresql" else "JSON"
    json_default = "'{}'::jsonb" if dialect == "postgresql" else "'{}'"

    if "author_kind" not in columns:
        sync_conn.exec_driver_sql("ALTER TABLE messages ADD COLUMN author_kind VARCHAR(40)")
    if "status_block_json" not in columns:
        sync_conn.exec_driver_sql(
            f"ALTER TABLE messages ADD COLUMN status_block_json {json_type} NOT NULL DEFAULT {json_default}"
        )
    if "context_block_json" not in columns:
        sync_conn.exec_driver_sql(
            f"ALTER TABLE messages ADD COLUMN context_block_json {json_type} NOT NULL DEFAULT {json_default}"
        )


async def bootstrap_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_message_contract_columns)
