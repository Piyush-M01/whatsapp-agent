"""Authentication agent — handles phone → client-ID → OTP verification flow."""

from __future__ import annotations

import logging

from whatsapp_agent.agents.base import AgentResponse, BaseAgent
from whatsapp_agent.services.client_api import ExternalClientAPI

logger = logging.getLogger(__name__)

# ── Session-state keys used by this agent ────────────────
AUTH_STATUS_KEY = "auth_status"
AUTH_USER_KEY = "auth_user_name"
AUTH_EMAIL_KEY = "auth_user_email"
AUTH_CLIENT_ID_KEY = "auth_client_id"

# Possible auth states
STATUS_AWAITING_PHONE = "awaiting_phone"
STATUS_AWAITING_CLIENT_ID = "awaiting_client_id"
STATUS_AWAITING_OTP = "awaiting_otp"
STATUS_AUTHENTICATED = "authenticated"


class AuthAgent(BaseAgent):
    """Authenticates a WhatsApp user via phone number or client code + OTP.

    Flow
    ----
    1. On first contact, the user's phone number (from WhatsApp metadata)
       is checked against the external client database API.
    2. If a match is found, an OTP is sent to the user's registered email.
    3. If no phone match, the user is asked for their client ID.
    4. If the client ID matches, an OTP is sent to the user's registered email.
    5. The user provides the OTP to complete verification.
    6. If neither phone nor client ID matches, the user is directed to support.
    """

    def __init__(self, client_api: ExternalClientAPI) -> None:
        self._api = client_api

    @property
    def name(self) -> str:
        return "AuthAgent"

    async def handle(self, message: str, session_state: dict) -> AgentResponse:
        """Route to the appropriate auth sub-step based on session state."""
        status = session_state.get(AUTH_STATUS_KEY, STATUS_AWAITING_PHONE)

        if status == STATUS_AUTHENTICATED:
            return AgentResponse(
                reply_text=(
                    f"You are already verified as *{session_state[AUTH_USER_KEY]}*. "
                    "How can I help you today?"
                )
            )

        if status == STATUS_AWAITING_OTP:
            return await self._handle_otp(message.strip(), session_state)

        if status == STATUS_AWAITING_CLIENT_ID:
            return await self._handle_client_id(message.strip(), session_state)

        # Default: first contact — try phone lookup
        return await self._handle_phone(message.strip(), session_state)

    # ── Private helpers ──────────────────────────────────

    async def _handle_phone(self, phone: str, session_state: dict) -> AgentResponse:
        """Look up phone via external API; on match → send OTP."""
        record = await self._api.lookup_by_phone(phone)
        if record:
            logger.info("Phone %s matched client %s", phone, record.client_id)
            return await self._initiate_otp(record.client_id, record.name, record.email, session_state)

        # Phone not found — ask for client code
        session_state[AUTH_STATUS_KEY] = STATUS_AWAITING_CLIENT_ID
        logger.info("Phone %s not found in external DB, requesting client ID", phone)
        return AgentResponse(
            reply_text=(
                "🔍 I couldn't find an account linked to this phone number.\n\n"
                "Please provide your *Client ID* so I can look you up."
            )
        )

    async def _handle_client_id(
        self, client_code: str, session_state: dict
    ) -> AgentResponse:
        """Look up client ID via external API; on match → send OTP."""
        record = await self._api.lookup_by_client_id(client_code)
        if not record:
            logger.info("Client ID %s not found in external DB", client_code)
            return AgentResponse(
                reply_text=(
                    "❌ Sorry, I couldn't find an account with that Client ID.\n\n"
                    "Please double-check and try again, or contact support for help."
                )
            )

        logger.info("Client ID %s matched: %s", client_code, record.name)
        return await self._initiate_otp(record.client_id, record.name, record.email, session_state)

    async def _initiate_otp(
        self, client_id: str, name: str, email: str, session_state: dict
    ) -> AgentResponse:
        """Send OTP and transition to the awaiting-OTP state."""
        session_state[AUTH_CLIENT_ID_KEY] = client_id
        session_state[AUTH_USER_KEY] = name
        session_state[AUTH_EMAIL_KEY] = email

        otp_sent = await self._api.send_otp(client_id)
        if not otp_sent:
            logger.error("Failed to send OTP for client %s", client_id)
            return AgentResponse(
                reply_text=(
                    "⚠️ We found your account but were unable to send the "
                    "verification code. Please try again later or contact support."
                )
            )

        session_state[AUTH_STATUS_KEY] = STATUS_AWAITING_OTP
        masked = self._mask_email(email)
        logger.info("OTP sent to %s for client %s", email, client_id)
        return AgentResponse(
            reply_text=(
                f"👤 Account found: *{name}*\n\n"
                f"A verification code has been sent to *{masked}*.\n"
                "Please enter the *6-digit OTP* to complete verification."
            )
        )

    async def _handle_otp(self, otp: str, session_state: dict) -> AgentResponse:
        """Verify the OTP provided by the user."""
        client_id = session_state.get(AUTH_CLIENT_ID_KEY, "")
        name = session_state.get(AUTH_USER_KEY, "")

        is_valid = await self._api.verify_otp(client_id, otp)
        if is_valid:
            session_state[AUTH_STATUS_KEY] = STATUS_AUTHENTICATED
            logger.info("User %s (client %s) authenticated via OTP", name, client_id)
            return AgentResponse(
                reply_text=(
                    f"✅ Verified! Welcome, *{name}*.\n\n"
                    "You have been successfully authenticated."
                )
            )

        logger.info("Invalid OTP for client %s", client_id)
        return AgentResponse(
            reply_text=(
                "❌ That code is incorrect or has expired.\n\n"
                "Please try again with the correct *6-digit OTP*."
            )
        )

    @staticmethod
    def _mask_email(email: str) -> str:
        """Mask an email for privacy: ``j***n@example.com``."""
        local, domain = email.split("@")
        if len(local) <= 2:
            masked_local = local[0] + "***"
        else:
            masked_local = local[0] + "***" + local[-1]
        return f"{masked_local}@{domain}"
