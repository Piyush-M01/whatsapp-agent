"""Tests for the AuthAgent — verifies the full authentication flow with OTP."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from whatsapp_agent.agents.auth_agent import (
    AUTH_CLIENT_ID_KEY,
    AUTH_STATUS_KEY,
    AUTH_USER_KEY,
    AuthAgent,
    STATUS_AUTHENTICATED,
    STATUS_AWAITING_CLIENT_ID,
    STATUS_AWAITING_OTP,
)
from whatsapp_agent.services.client_api import ClientRecord, ExternalClientAPI


# ── Helper to build a mocked ExternalClientAPI ───────────

def _mock_api(
    phone_record: ClientRecord | None = None,
    client_id_record: ClientRecord | None = None,
    otp_send_ok: bool = True,
    otp_valid: bool = True,
) -> ExternalClientAPI:
    """Return an ``ExternalClientAPI`` with all methods mocked."""
    api = ExternalClientAPI.__new__(ExternalClientAPI)
    api.lookup_by_phone = AsyncMock(return_value=phone_record)
    api.lookup_by_client_id = AsyncMock(return_value=client_id_record)
    api.send_otp = AsyncMock(return_value=otp_send_ok)
    api.verify_otp = AsyncMock(return_value=otp_valid)
    return api


_ALICE = ClientRecord(client_id="ACME-1001", name="Alice Johnson", email="alice@example.com")
_CAROL = ClientRecord(client_id="GLX-2001", name="Carol Davis", email="carol@example.com")


# ──────────────────────────────────────────────────────────
# Test 1: Phone match → OTP sent → correct OTP → authenticated
# ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_phone_match_otp_flow():
    api = _mock_api(phone_record=_ALICE, otp_valid=True)
    agent = AuthAgent(client_api=api)
    state: dict = {}

    # Step 1: Phone lookup matches → OTP sent
    response = await agent.handle("+15551234567", state)
    assert "Alice Johnson" in response.reply_text
    assert "verification code" in response.reply_text.lower()
    assert state[AUTH_STATUS_KEY] == STATUS_AWAITING_OTP
    api.lookup_by_phone.assert_called_once_with("+15551234567")
    api.send_otp.assert_called_once_with("ACME-1001")

    # Step 2: User provides correct OTP → authenticated
    response = await agent.handle("123456", state)
    assert "Verified" in response.reply_text
    assert state[AUTH_STATUS_KEY] == STATUS_AUTHENTICATED
    api.verify_otp.assert_called_once_with("ACME-1001", "123456")


# ──────────────────────────────────────────────────────────
# Test 2: Phone miss → client ID match → OTP → authenticated
# ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_client_id_fallback_otp_flow():
    api = _mock_api(phone_record=None, client_id_record=_CAROL, otp_valid=True)
    agent = AuthAgent(client_api=api)
    state: dict = {}

    # Step 1: Unknown phone → asks for client ID
    response = await agent.handle("+10000000000", state)
    assert "Client ID" in response.reply_text
    assert state[AUTH_STATUS_KEY] == STATUS_AWAITING_CLIENT_ID

    # Step 2: Valid client ID → OTP sent
    response = await agent.handle("GLX-2001", state)
    assert "Carol Davis" in response.reply_text
    assert "verification code" in response.reply_text.lower()
    assert state[AUTH_STATUS_KEY] == STATUS_AWAITING_OTP

    # Step 3: Correct OTP → authenticated
    response = await agent.handle("654321", state)
    assert "Verified" in response.reply_text
    assert state[AUTH_STATUS_KEY] == STATUS_AUTHENTICATED


# ──────────────────────────────────────────────────────────
# Test 3: Phone miss → client ID miss
# ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_no_match():
    api = _mock_api(phone_record=None, client_id_record=None)
    agent = AuthAgent(client_api=api)
    state: dict = {}

    # Step 1: Unknown phone
    response = await agent.handle("+19999999999", state)
    assert state[AUTH_STATUS_KEY] == STATUS_AWAITING_CLIENT_ID

    # Step 2: Unknown client code
    response = await agent.handle("INVALID-CODE", state)
    assert "couldn't find" in response.reply_text.lower() or "sorry" in response.reply_text.lower()


# ──────────────────────────────────────────────────────────
# Test 4: Wrong OTP → retry → correct OTP
# ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_wrong_otp_then_correct():
    api = _mock_api(phone_record=_ALICE, otp_valid=False)
    agent = AuthAgent(client_api=api)
    state: dict = {}

    # Step 1: Phone match → OTP sent
    await agent.handle("+15551234567", state)
    assert state[AUTH_STATUS_KEY] == STATUS_AWAITING_OTP

    # Step 2: Wrong OTP → stay in awaiting_otp
    response = await agent.handle("000000", state)
    assert "incorrect" in response.reply_text.lower() or "expired" in response.reply_text.lower()
    assert state[AUTH_STATUS_KEY] == STATUS_AWAITING_OTP

    # Step 3: Now mock returns valid
    api.verify_otp = AsyncMock(return_value=True)
    response = await agent.handle("123456", state)
    assert "Verified" in response.reply_text
    assert state[AUTH_STATUS_KEY] == STATUS_AUTHENTICATED


# ──────────────────────────────────────────────────────────
# Test 5: Already authenticated user
# ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_already_authenticated():
    api = _mock_api()
    agent = AuthAgent(client_api=api)
    state = {AUTH_STATUS_KEY: STATUS_AUTHENTICATED, AUTH_USER_KEY: "Alice Johnson"}

    response = await agent.handle("anything", state)
    assert "already verified" in response.reply_text.lower()
    assert "Alice Johnson" in response.reply_text


# ──────────────────────────────────────────────────────────
# Test 6: OTP send failure
# ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_otp_send_failure():
    api = _mock_api(phone_record=_ALICE, otp_send_ok=False)
    agent = AuthAgent(client_api=api)
    state: dict = {}

    response = await agent.handle("+15551234567", state)
    assert "unable to send" in response.reply_text.lower()
    # Should NOT have moved to awaiting_otp since send failed
    assert state.get(AUTH_STATUS_KEY) != STATUS_AWAITING_OTP
