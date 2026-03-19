import asyncio

from app.db.bootstrap import bootstrap_database


async def main() -> None:
    await bootstrap_database()
    print("database initialized")


if __name__ == "__main__":
    asyncio.run(main())

