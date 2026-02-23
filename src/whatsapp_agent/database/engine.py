"""Database engine and async session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from whatsapp_agent.config import settings
from whatsapp_agent.models.user import Base

engine = create_async_engine(settings.database_url, echo=settings.debug)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables that don't yet exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session, rolling back on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
