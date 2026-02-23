"""Tests for the UserRepository."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from whatsapp_agent.database.repository import UserRepository
from whatsapp_agent.models.user import Base, User

# ── In-memory test database ─────────────────────────────
_test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
_test_session_factory = async_sessionmaker(_test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session():
    """Create tables in a fresh in-memory DB and yield a session."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _test_session_factory() as session:
        # Seed test data
        session.add_all(
            [
                User(
                    client_id="test_client",
                    client_code="TC-001",
                    name="Test User",
                    phone="+15551234567",
                    email="test@example.com",
                ),
                User(
                    client_id="other_client",
                    client_code="OC-001",
                    name="Other User",
                    phone="+442071111111",
                    email="other@example.com",
                ),
            ]
        )
        await session.commit()
        yield session

    # Tear down
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_by_phone_match(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user = await repo.find_by_phone("+15551234567")
    assert user is not None
    assert user.name == "Test User"
    assert user.client_code == "TC-001"


@pytest.mark.asyncio
async def test_find_by_phone_no_match(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user = await repo.find_by_phone("+10000000000")
    assert user is None


@pytest.mark.asyncio
async def test_find_by_client_code_match(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user = await repo.find_by_client_code("OC-001")
    assert user is not None
    assert user.name == "Other User"
    assert user.phone == "+442071111111"


@pytest.mark.asyncio
async def test_find_by_client_code_no_match(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user = await repo.find_by_client_code("NONEXISTENT")
    assert user is None
