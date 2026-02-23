"""Email service — sends confirmation emails via async SMTP."""

from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from whatsapp_agent.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Sends transactional emails using the configured SMTP server."""

    async def send_confirmation(self, to_email: str, user_name: str) -> None:
        """Send an account-verification confirmation email.

        Parameters
        ----------
        to_email:
            Recipient email address.
        user_name:
            Name of the user (used in the greeting).
        """
        subject = f"WhatsApp Verification Confirmed — {settings.app_name}"
        body = (
            f"Hello {user_name},\n\n"
            f"Your identity has been successfully verified on {settings.app_name} "
            f"via WhatsApp.\n\n"
            "If you did not initiate this verification, please contact support "
            "immediately.\n\n"
            "Best regards,\n"
            f"The {settings.app_name} Team"
        )

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to_email
        msg.set_content(body)

        logger.info("Sending confirmation email to %s", to_email)

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=True,
        )

        logger.info("Confirmation email sent to %s", to_email)
