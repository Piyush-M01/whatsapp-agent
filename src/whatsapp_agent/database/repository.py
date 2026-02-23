"""User repository — data access layer for user lookups."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whatsapp_agent.models.user import User


class UserRepository:
    """Encapsulates all database queries related to users."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_phone(self, phone: str) -> User | None:
        """Look up a user by their phone number.

        The phone is expected in E.164 format (e.g. ``+15551234567``).
        """
        stmt = select(User).where(User.phone == phone, User.is_active.is_(True))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_client_code(self, client_code: str) -> User | None:
        """Look up a user by their client-issued code."""
        stmt = select(User).where(
            User.client_code == client_code, User.is_active.is_(True)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
