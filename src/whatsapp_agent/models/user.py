"""SQLAlchemy User model."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class User(Base):
    """Represents a registered customer in the system.

    Each user belongs to a specific client (company) and is identified
    by their phone number or unique client code.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(
        String(64), nullable=False, doc="ID of the company/client this user belongs to"
    )
    client_code: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, doc="User-facing code for fallback auth"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_users_phone", "phone"),
        Index("ix_users_client_code", "client_code"),
        Index("ix_users_client_id", "client_id"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name!r} phone={self.phone!r}>"
