"""WhatsApp Agent Framework — configuration loaded from environment."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide settings, loaded from .env or environment variables."""

    # ── Database ──────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./whatsapp_agent.db"

    # ── WhatsApp Business API ─────────────────────────────
    whatsapp_verify_token: str = "changeme"
    whatsapp_api_token: str = ""
    whatsapp_phone_number_id: str = ""

    # ── SMTP Email ────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@yourcompany.com"

    # ── App ───────────────────────────────────────────────
    app_name: str = "WhatsApp Agent"
    debug: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton settings instance
settings = Settings()
