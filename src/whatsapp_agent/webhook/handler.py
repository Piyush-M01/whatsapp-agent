"""WhatsApp webhook handler — receives and responds to messages."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Query, Request, Response

from whatsapp_agent.config import settings
from whatsapp_agent.database.engine import async_session_factory
from whatsapp_agent.services.message_router import MessageRouter
from whatsapp_agent.services.session_manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])

# ── Shared instances (created once, reused across requests) ──
_session_manager = SessionManager()
_message_router = MessageRouter(_session_manager)


# ──────────────────────────────────────────────────────────────
# GET /webhook — Meta verification challenge
# ──────────────────────────────────────────────────────────────
@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> Response:
    """Respond to the Meta webhook verification challenge."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("Webhook verified successfully")
        return Response(content=hub_challenge, media_type="text/plain")
    logger.warning("Webhook verification failed (bad token or mode)")
    return Response(content="Forbidden", status_code=403)


# ──────────────────────────────────────────────────────────────
# POST /webhook — Incoming messages
# ──────────────────────────────────────────────────────────────
@router.post("/webhook")
async def receive_message(request: Request) -> dict:
    """Process an incoming WhatsApp message via the Meta Cloud API.

    Expected payload structure (simplified)::

        {
          "entry": [{
            "changes": [{
              "value": {
                "messages": [{
                  "from": "+15551234567",
                  "text": { "body": "Hello!" }
                }]
              }
            }]
          }]
        }
    """
    body = await request.json()

    # Extract message data from the Meta payload
    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages", [])
    except (KeyError, IndexError):
        logger.debug("Received non-message webhook event, ignoring")
        return {"status": "ok"}

    for msg in messages:
        sender_phone = msg.get("from", "")
        text_body = msg.get("text", {}).get("body", "")

        if not sender_phone or not text_body:
            continue

        logger.info("Message from %s: %s", sender_phone, text_body[:80])

        # Handle logout
        if text_body.strip().lower() == "logout":
            _session_manager.clear(sender_phone)
            await _send_whatsapp_reply(
                sender_phone, "👋 You have been logged out. Send any message to start again."
            )
            continue

        # Route through the framework
        async with async_session_factory() as db_session:
            response = await _message_router.route(
                phone=sender_phone,
                message=text_body,
                db_session=db_session,
            )
            await db_session.commit()

        await _send_whatsapp_reply(sender_phone, response.reply_text)

    return {"status": "ok"}


# ──────────────────────────────────────────────────────────────
# WhatsApp reply helper
# ──────────────────────────────────────────────────────────────
async def _send_whatsapp_reply(to_phone: str, text: str) -> None:
    """Send a text reply back to the user via the WhatsApp Cloud API."""
    if not settings.whatsapp_api_token:
        logger.warning("WHATSAPP_API_TOKEN not set — reply logged only: %s", text)
        return

    url = (
        f"https://graph.facebook.com/v21.0/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code == 200:
        logger.info("Reply sent to %s", to_phone)
    else:
        logger.error(
            "Failed to send reply to %s: %s %s", to_phone, resp.status_code, resp.text
        )
