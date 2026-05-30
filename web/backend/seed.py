"""Seed default admin user on first startup."""

import asyncio
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.auth import hash_password
from web.backend.database import async_session, init_db
from web.backend.models import User


async def seed_admin(
    username: str = "admin",
    password: str = "admin123",
) -> None:
    await init_db()
    async with async_session() as db:
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none() is not None:
            return  # Admin already exists

        admin = User(
            username=username,
            password_hash=hash_password(password),
            is_admin=True,
        )
        db.add(admin)
        await db.commit()
        print(f"Admin user created: {username} / {password}")


if __name__ == "__main__":
    user = os.environ.get("INSIGHTOR_ADMIN_USER", "admin")
    pwd = os.environ.get("INSIGHTOR_ADMIN_PASS", "admin123")
    asyncio.run(seed_admin(user, pwd))
