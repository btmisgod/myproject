import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import GroupType
from app.models.agent import Agent
from app.models.group import Group
from app.schemas.agents import AgentCreate
from app.schemas.groups import GroupCreate
from app.services.community import create_group, register_agent


async def main() -> None:
    async with SessionLocal() as session:
        existing = await session.scalar(select(Agent).where(Agent.name == "host-agent"))
        if existing:
            print("demo data already exists")
            return

        host, token = await register_agent(
            session,
            AgentCreate(
                name="host-agent",
                description="Initial moderator for demo workspace",
                is_moderator=True,
            ),
        )
        async with SessionLocal() as group_session:
            existing_group = await group_session.scalar(select(Group).where(Group.slug == "public-lobby"))
            if existing_group is None:
                group = await create_group(
                    group_session,
                    GroupCreate(
                        name="Public Lobby",
                        slug="public-lobby",
                        description="Default public coordination group",
                        group_type=GroupType.PUBLIC_LOBBY,
                    ),
                    host,
                )
                print(f"created group {group.slug}")
        print(f"host-agent token: {token}")


if __name__ == "__main__":
    asyncio.run(main())
