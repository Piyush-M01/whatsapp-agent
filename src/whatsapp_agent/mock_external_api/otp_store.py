"""In-memory OTP store with expiry — used by the mock external API."""

from __future__ import annotations

import logging
import random
import string
import time

logger = logging.getLogger(__name__)

# OTP validity period in seconds
OTP_TTL_SECONDS = 300  # 5 minutes


class OTPStore:
    """Thread-safe-ish in-memory OTP store.

    Each entry maps ``client_id → (otp_code, created_at)``.
    Old entries are lazily purged on access.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}

    def generate(self, client_id: str) -> str:
        """Generate and store a 6-digit OTP for *client_id*."""
        code = "".join(random.choices(string.digits, k=6))
        self._store[client_id] = (code, time.time())
        logger.info("OTP generated for client %s: %s", client_id, code)
        return code

    def verify(self, client_id: str, otp: str) -> bool:
        """Return ``True`` if *otp* matches the stored code and is not expired."""
        entry = self._store.get(client_id)
        if entry is None:
            return False
        stored_otp, created_at = entry
        if time.time() - created_at > OTP_TTL_SECONDS:
            # Expired — remove it
            self._store.pop(client_id, None)
            logger.info("OTP expired for client %s", client_id)
            return False
        if otp == stored_otp:
            # Consume the OTP on successful verification
            self._store.pop(client_id, None)
            return True
        return False
