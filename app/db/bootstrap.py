from sqlalchemy import inspect, select, update

import app.models  # noqa: F401
from app.db.session import engine
from app.models.base import Base
from app.models.group import Group
from app.services.channel_protocol_binding import sanitize_group_metadata


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


def _cleanup_group_metadata_residue(sync_conn) -> None:
    inspector = inspect(sync_conn)
    if "groups" not in inspector.get_table_names():
        return

    rows = sync_conn.execute(select(Group.id, Group.metadata_json)).all()
    for group_id, metadata_json in rows:
        cleaned = sanitize_group_metadata(metadata_json if isinstance(metadata_json, dict) else {})
        if cleaned != (metadata_json if isinstance(metadata_json, dict) else {}):
            sync_conn.execute(
                update(Group)
                .where(Group.id == group_id)
                .values(metadata_json=cleaned)
            )


async def bootstrap_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_message_contract_columns)
        await conn.run_sync(_cleanup_group_metadata_residue)
