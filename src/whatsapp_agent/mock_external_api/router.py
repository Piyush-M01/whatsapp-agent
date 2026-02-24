"""Mock external API router — simulates the customer's external database API.

Endpoints
---------
GET  /clients/lookup?phone=...   → client info by phone
GET  /clients/{client_id}        → client info by client ID
POST /otp/send                   → trigger OTP delivery
POST /otp/verify                 → validate OTP
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from whatsapp_agent.database.engine import async_session_factory
from whatsapp_agent.database.repository import UserRepository
from whatsapp_agent.mock_external_api.otp_store import OTPStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/external/v1", tags=["mock-external-api"])

# Shared OTP store (in-memory singleton)
_otp_store = OTPStore()


# ── Response / request models ────────────────────────────

class ClientInfo(BaseModel):
    client_id: str
    name: str
    email: str


class OTPSendRequest(BaseModel):
    client_id: str


class OTPSendResponse(BaseModel):
    success: bool
    message: str


class OTPVerifyRequest(BaseModel):
    client_id: str
    otp: str


class OTPVerifyResponse(BaseModel):
    valid: bool


# ── Endpoints ────────────────────────────────────────────

@router.get("/clients/lookup", response_model=ClientInfo)
async def lookup_by_phone(phone: str = Query(..., description="Phone in E.164 format")):
    """Look up a client by phone number."""
    async with async_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.find_by_phone(phone)

    if not user:
        raise HTTPException(status_code=404, detail="No client found for this phone number")

    return ClientInfo(client_id=user.client_code, name=user.name, email=user.email)


@router.get("/clients/{client_id}", response_model=ClientInfo)
async def lookup_by_client_id(client_id: str):
    """Look up a client by their client ID / code."""
    async with async_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.find_by_client_code(client_id)

    if not user:
        raise HTTPException(status_code=404, detail="No client found for this ID")

    return ClientInfo(client_id=user.client_code, name=user.name, email=user.email)


@router.post("/otp/send", response_model=OTPSendResponse)
async def send_otp(body: OTPSendRequest):
    """Generate an OTP for the given client.

    In a real system this would dispatch an email/SMS.
    Here we just log the OTP and store it.
    """
    # Verify client exists first
    async with async_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.find_by_client_code(body.client_id)

    if not user:
        raise HTTPException(status_code=404, detail="Client not found")

    code = _otp_store.generate(body.client_id)
    # In a real system this would send an email; here we log it for testing
    logger.info(
        "📧 OTP for %s (%s): %s  (would be sent to %s)",
        user.name,
        body.client_id,
        code,
        user.email,
    )
    return OTPSendResponse(success=True, message=f"OTP sent to {user.email}")


@router.post("/otp/verify", response_model=OTPVerifyResponse)
async def verify_otp(body: OTPVerifyRequest):
    """Validate an OTP for the given client."""
    is_valid = _otp_store.verify(body.client_id, body.otp)
    if is_valid:
        logger.info("OTP verified for %s", body.client_id)
    else:
        logger.info("OTP verification failed for %s", body.client_id)
    return OTPVerifyResponse(valid=is_valid)
