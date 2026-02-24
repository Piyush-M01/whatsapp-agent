"""External Client API — async HTTP client for the external database API.

This service wraps all calls to the external (or mock) client database
and OTP verification API.  In production the ``base_url`` would point
to the customer's real API; for the PoC it points to the co-located
mock API at ``/external/v1``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from whatsapp_agent.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ClientRecord:
    """Lightweight value object returned by lookup methods."""

    client_id: str
    name: str
    email: str


class ExternalClientAPI:
    """Async HTTP wrapper around the external client database + OTP API."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or settings.external_api_base_url).rstrip("/")

    # ── Client lookups ───────────────────────────────────

    async def lookup_by_phone(self, phone: str) -> ClientRecord | None:
        """Look up a client by phone number.

        Returns a ``ClientRecord`` on success, ``None`` if not found.
        """
        url = f"{self._base_url}/clients/lookup"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params={"phone": phone})
            if resp.status_code == 200:
                data = resp.json()
                return ClientRecord(
                    client_id=data["client_id"],
                    name=data["name"],
                    email=data["email"],
                )
            if resp.status_code == 404:
                return None
            logger.error("Phone lookup failed: %s %s", resp.status_code, resp.text)
            return None
        except httpx.HTTPError as exc:
            logger.exception("Phone lookup request error: %s", exc)
            return None

    async def lookup_by_client_id(self, client_id: str) -> ClientRecord | None:
        """Look up a client by their client ID / code.

        Returns a ``ClientRecord`` on success, ``None`` if not found.
        """
        url = f"{self._base_url}/clients/{client_id}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return ClientRecord(
                    client_id=data["client_id"],
                    name=data["name"],
                    email=data["email"],
                )
            if resp.status_code == 404:
                return None
            logger.error("Client ID lookup failed: %s %s", resp.status_code, resp.text)
            return None
        except httpx.HTTPError as exc:
            logger.exception("Client ID lookup request error: %s", exc)
            return None

    # ── OTP ──────────────────────────────────────────────

    async def send_otp(self, client_id: str) -> bool:
        """Request OTP delivery for *client_id*.

        Returns ``True`` if the OTP was sent successfully.
        """
        url = f"{self._base_url}/otp/send"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json={"client_id": client_id})
            if resp.status_code == 200:
                data = resp.json()
                logger.info("OTP send result for %s: %s", client_id, data.get("message"))
                return data.get("success", False)
            logger.error("OTP send failed: %s %s", resp.status_code, resp.text)
            return False
        except httpx.HTTPError as exc:
            logger.exception("OTP send request error: %s", exc)
            return False

    async def verify_otp(self, client_id: str, otp: str) -> bool:
        """Validate an OTP for *client_id*.

        Returns ``True`` if the OTP is correct and not expired.
        """
        url = f"{self._base_url}/otp/verify"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url, json={"client_id": client_id, "otp": otp}
                )
            if resp.status_code == 200:
                return resp.json().get("valid", False)
            logger.error("OTP verify failed: %s %s", resp.status_code, resp.text)
            return False
        except httpx.HTTPError as exc:
            logger.exception("OTP verify request error: %s", exc)
            return False
