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

    # ── External Client API ───────────────────────────────
    external_api_base_url: str = "http://localhost:8000/external/v1"

    # ── App ───────────────────────────────────────────────
    app_name: str = "WhatsApp Agent"
    debug: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton settings instance
settings = Settings()
