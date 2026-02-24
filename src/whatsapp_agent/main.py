"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from whatsapp_agent.config import settings
from whatsapp_agent.database.engine import init_db
from whatsapp_agent.mock_external_api.router import router as mock_api_router
from whatsapp_agent.webhook.handler import router as webhook_router

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    logger.info("Starting %s …", settings.app_name)
    await init_db()
    logger.info("Database initialised")
    yield
    logger.info("Shutting down %s …", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="Agentic AI framework for WhatsApp Business customer interactions",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(webhook_router)
app.include_router(mock_api_router)


@app.get("/health")
async def health_check():
    """Simple liveness probe."""
    return {"status": "healthy", "app": settings.app_name}
