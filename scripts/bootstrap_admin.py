import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.admin_user import AdminUser
from app.schemas.auth import AdminUserCreate
from app.services.auth import register_admin_user


async def main() -> None:
    async with SessionLocal() as session:
        existing = await session.scalar(select(AdminUser).where(AdminUser.username == "admin"))
        if existing:
            print("admin user already exists: admin")
            return
        admin_user, access_token = await register_admin_user(
            session,
            AdminUserCreate(
                username="admin",
                display_name="Community Admin",
                password="Admin123456!",
                email=None,
            ),
        )
        print(f"created admin user: {admin_user.username}")
        print(f"access token: {access_token}")


if __name__ == "__main__":
    asyncio.run(main())

