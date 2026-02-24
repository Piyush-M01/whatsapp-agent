"""Message router — dispatches incoming messages to the correct agent."""

from __future__ import annotations

import logging

from whatsapp_agent.agents.auth_agent import AuthAgent
from whatsapp_agent.agents.base import AgentResponse
from whatsapp_agent.services.client_api import ExternalClientAPI
from whatsapp_agent.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


class MessageRouter:
    """Central router that decides which agent handles a message.

    Routing logic
    -------------
    * If the user is **not** authenticated → ``AuthAgent``
    * If the user **is** authenticated → placeholder for future task agents
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self._session_manager = session_manager

    async def route(self, phone: str, message: str) -> AgentResponse:
        """Route a message to the appropriate agent and return its response.

        Parameters
        ----------
        phone:
            The sender's phone number (from WhatsApp metadata).
        message:
            The raw text body of the message.
        """
        session = self._session_manager.get(phone)

        if not session.is_authenticated:
            # First contact or mid-auth flow
            client_api = ExternalClientAPI()
            agent = AuthAgent(client_api=client_api)
            logger.info("Routing %s → %s", phone, agent.name)

            # On first message, use the phone itself for lookup
            if "auth_status" not in session.state:
                response = await agent.handle(phone, session.state)
            else:
                response = await agent.handle(message, session.state)
            return response

        # ── Authenticated — future task routing goes here ─────
        # For now, echo that the user is authenticated.
        logger.info("User %s is authenticated; no task agent registered yet", phone)
        return AgentResponse(
            reply_text=(
                f"👋 Hello, *{session.state.get('auth_user_name', 'there')}*! "
                "You are verified. Task-based features are coming soon.\n\n"
                "Type *logout* to end your session."
            )
        )
