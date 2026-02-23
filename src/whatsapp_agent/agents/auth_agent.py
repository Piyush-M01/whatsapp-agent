"""Authentication agent — handles the phone → client-ID → email verification flow."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from whatsapp_agent.agents.base import AgentResponse, BaseAgent
from whatsapp_agent.database.repository import UserRepository
from whatsapp_agent.services.email_service import EmailService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ── Session-state keys used by this agent ────────────────
AUTH_STATUS_KEY = "auth_status"
AUTH_USER_KEY = "auth_user_name"
AUTH_EMAIL_KEY = "auth_user_email"

# Possible auth states
STATUS_AWAITING_PHONE = "awaiting_phone"
STATUS_AWAITING_CLIENT_ID = "awaiting_client_id"
STATUS_AUTHENTICATED = "authenticated"


class AuthAgent(BaseAgent):
    """Authenticates a WhatsApp user via phone number or client code.

    Flow
    ----
    1. On first contact, the user's phone number (from WhatsApp metadata)
       is checked against the database.
    2. If no match, the user is asked for their client code.
    3. If the client code matches, a confirmation email is sent.
    4. If neither matches, the user is directed to support.
    """

    def __init__(self, db_session: AsyncSession, email_service: EmailService) -> None:
        self._repo = UserRepository(db_session)
        self._email = email_service

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

        if status == STATUS_AWAITING_CLIENT_ID:
            return await self._handle_client_id(message.strip(), session_state)

        # Default: first contact — try phone lookup
        return await self._handle_phone(message.strip(), session_state)

    # ── Private helpers ──────────────────────────────────

    async def _handle_phone(self, phone: str, session_state: dict) -> AgentResponse:
        """Attempt authentication by phone number."""
        user = await self._repo.find_by_phone(phone)
        if user:
            session_state[AUTH_STATUS_KEY] = STATUS_AUTHENTICATED
            session_state[AUTH_USER_KEY] = user.name
            session_state[AUTH_EMAIL_KEY] = user.email
            logger.info("User %s authenticated via phone %s", user.name, phone)
            return AgentResponse(
                reply_text=(
                    f"✅ Welcome back, *{user.name}*! "
                    "You have been successfully verified."
                )
            )

        # Phone not found — ask for client code
        session_state[AUTH_STATUS_KEY] = STATUS_AWAITING_CLIENT_ID
        logger.info("Phone %s not found, requesting client code", phone)
        return AgentResponse(
            reply_text=(
                "🔍 I couldn't find an account linked to this phone number.\n\n"
                "Please provide your *Client ID* so I can look you up."
            )
        )

    async def _handle_client_id(
        self, client_code: str, session_state: dict
    ) -> AgentResponse:
        """Attempt authentication by client code and send confirmation email."""
        user = await self._repo.find_by_client_code(client_code)
        if not user:
            logger.info("Client code %s not found", client_code)
            return AgentResponse(
                reply_text=(
                    "❌ Sorry, I couldn't find an account with that Client ID.\n\n"
                    "Please double-check and try again, or contact support for help."
                )
            )

        # Match found — send confirmation email
        session_state[AUTH_STATUS_KEY] = STATUS_AUTHENTICATED
        session_state[AUTH_USER_KEY] = user.name
        session_state[AUTH_EMAIL_KEY] = user.email

        masked_email = self._mask_email(user.email)

        try:
            await self._email.send_confirmation(
                to_email=user.email,
                user_name=user.name,
            )
            logger.info(
                "User %s authenticated via client code; confirmation sent to %s",
                user.name,
                user.email,
            )
            return AgentResponse(
                reply_text=(
                    f"✅ Verified! Welcome, *{user.name}*.\n\n"
                    f"A confirmation email has been sent to *{masked_email}*."
                )
            )
        except Exception:
            logger.exception("Failed to send confirmation email to %s", user.email)
            return AgentResponse(
                reply_text=(
                    f"✅ Verified! Welcome, *{user.name}*.\n\n"
                    "⚠️ However, I was unable to send the confirmation email. "
                    "Please contact support if you need the confirmation."
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
