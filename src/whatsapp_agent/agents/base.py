"""Base agent — abstract interface every agent must implement."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AgentResponse:
    """Value object returned by an agent after processing a message."""

    reply_text: str
    end_conversation: bool = False


class BaseAgent(ABC):
    """Abstract base class for all conversational agents.

    Every agent receives the raw message text and the current session
    state dict.  It returns an ``AgentResponse`` containing the reply
    to send back to the user.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable agent name (used in logs and routing)."""

    @abstractmethod
    async def handle(
        self,
        message: str,
        session_state: dict,
    ) -> AgentResponse:
        """Process a user message and return a response.

        Parameters
        ----------
        message:
            The raw text the user sent.
        session_state:
            Mutable dict persisted across turns for this user's session.
            Agents may read and write keys to track conversation state.
        """
