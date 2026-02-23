"""Tests for the AuthAgent — verifies the full authentication flow."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock, patch

from whatsapp_agent.agents.auth_agent import (
    AuthAgent,
    STATUS_AUTHENTICATED,
    STATUS_AWAITING_CLIENT_ID,
    AUTH_STATUS_KEY,
    AUTH_USER_KEY,
)
from whatsapp_agent.models.user import Base, User
from whatsapp_agent.services.email_service import EmailService

# ── In-memory test database ─────────────────────────────
_test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
_test_session_factory = async_sessionmaker(_test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session():
    """Create tables and seed test users."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _test_session_factory() as session:
        session.add_all(
            [
                User(
                    client_id="acme",
                    client_code="ACME-1001",
                    name="Alice Johnson",
                    phone="+15551234567",
                    email="alice@example.com",
                ),
                User(
                    client_id="globex",
                    client_code="GLX-2001",
                    name="Carol Davis",
                    phone="+442071234567",
                    email="carol@example.com",
                ),
            ]
        )
        await session.commit()
        yield session

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def email_service():
    """Mocked email service — never actually sends emails."""
    svc = EmailService()
    svc.send_confirmation = AsyncMock()
    return svc


# ──────────────────────────────────────────────────────────
# Test 1: Phone number matches
# ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_phone_match(db_session, email_service):
    agent = AuthAgent(db_session=db_session, email_service=email_service)
    state: dict = {}

    response = await agent.handle("+15551234567", state)

    assert "Welcome back" in response.reply_text
    assert "Alice Johnson" in response.reply_text
    assert state[AUTH_STATUS_KEY] == STATUS_AUTHENTICATED
    assert state[AUTH_USER_KEY] == "Alice Johnson"
    # No email should be sent for phone-match flow
    email_service.send_confirmation.assert_not_called()


# ──────────────────────────────────────────────────────────
# Test 2: Phone miss → client ID match → email sent
# ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_client_id_fallback(db_session, email_service):
    agent = AuthAgent(db_session=db_session, email_service=email_service)
    state: dict = {}

    # Step 1: Unknown phone
    response = await agent.handle("+10000000000", state)
    assert "Client ID" in response.reply_text
    assert state[AUTH_STATUS_KEY] == STATUS_AWAITING_CLIENT_ID

    # Step 2: Provide valid client code
    response = await agent.handle("GLX-2001", state)
    assert "Verified" in response.reply_text or "Welcome" in response.reply_text
    assert "Carol Davis" in response.reply_text
    assert state[AUTH_STATUS_KEY] == STATUS_AUTHENTICATED

    # Confirmation email should have been sent
    email_service.send_confirmation.assert_called_once_with(
        to_email="carol@example.com",
        user_name="Carol Davis",
    )


# ──────────────────────────────────────────────────────────
# Test 3: Phone miss → client ID miss
# ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_no_match(db_session, email_service):
    agent = AuthAgent(db_session=db_session, email_service=email_service)
    state: dict = {}

    # Step 1: Unknown phone
    response = await agent.handle("+19999999999", state)
    assert state[AUTH_STATUS_KEY] == STATUS_AWAITING_CLIENT_ID

    # Step 2: Unknown client code
    response = await agent.handle("INVALID-CODE", state)
    assert "couldn't find" in response.reply_text.lower() or "sorry" in response.reply_text.lower()
    email_service.send_confirmation.assert_not_called()


# ──────────────────────────────────────────────────────────
# Test 4: Already authenticated user
# ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_already_authenticated(db_session, email_service):
    agent = AuthAgent(db_session=db_session, email_service=email_service)
    state = {AUTH_STATUS_KEY: STATUS_AUTHENTICATED, AUTH_USER_KEY: "Alice Johnson"}

    response = await agent.handle("anything", state)
    assert "already verified" in response.reply_text.lower()
    assert "Alice Johnson" in response.reply_text
