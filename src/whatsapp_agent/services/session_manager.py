"""Session manager — tracks per-user conversation state."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents the current conversation state for one user."""

    user_phone: str
    state: dict[str, Any] = field(default_factory=dict)

    @property
    def is_authenticated(self) -> bool:
        return self.state.get("auth_status") == "authenticated"


class SessionManager:
    """In-memory session store keyed by the sender's phone number.

    For production deployments, swap to a Redis-backed implementation
    by sub-classing and overriding :pymethod:`get` / :pymethod:`_save`.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get(self, phone: str) -> Session:
        """Retrieve or create a session for the given phone number."""
        if phone not in self._sessions:
            logger.info("Creating new session for %s", phone)
            self._sessions[phone] = Session(user_phone=phone)
        return self._sessions[phone]

    def clear(self, phone: str) -> None:
        """Remove a session (e.g. on logout or timeout)."""
        self._sessions.pop(phone, None)
        logger.info("Session cleared for %s", phone)

    @property
    def active_count(self) -> int:
        """Number of active sessions (useful for monitoring)."""
        return len(self._sessions)
