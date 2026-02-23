"""Seed script — populates the database with sample users for testing."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from whatsapp_agent.database.engine import async_session_factory, init_db
from whatsapp_agent.models.user import User

SAMPLE_USERS = [
    User(
        client_id="acme_corp",
        client_code="ACME-1001",
        name="Alice Johnson",
        phone="+15551234567",
        email="alice@example.com",
    ),
    User(
        client_id="acme_corp",
        client_code="ACME-1002",
        name="Bob Smith",
        phone="+15559876543",
        email="bob@example.com",
    ),
    User(
        client_id="globex_inc",
        client_code="GLX-2001",
        name="Carol Davis",
        phone="+442071234567",
        email="carol@example.com",
    ),
    User(
        client_id="globex_inc",
        client_code="GLX-2002",
        name="Dan Wilson",
        phone="+919876543210",
        email="dan@example.com",
    ),
]


async def seed() -> None:
    """Insert sample users into the database."""
    await init_db()
    async with async_session_factory() as session:
        session: AsyncSession
        for user in SAMPLE_USERS:
            session.add(user)
        await session.commit()
    print(f"✅ Seeded {len(SAMPLE_USERS)} users into the database.")


if __name__ == "__main__":
    asyncio.run(seed())
