"""SQLAlchemy async database session and ORM models.

Models are infrastructure types — they mirror proto-defined shapes but are NOT
business domain types. Business logic never imports from this module directly;
only domain functions use the session provided by the dependency.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=(settings.environment == "development"),
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency — yields an async DB session."""
    async with async_session_factory() as session:
        yield session  # type: ignore[misc]


class Base(DeclarativeBase):
    pass


class GigStatus(enum.StrEnum):
    GIG_STATUS_UNSPECIFIED = "GIG_STATUS_UNSPECIFIED"
    GIG_STATUS_DRAFT = "GIG_STATUS_DRAFT"
    GIG_STATUS_OPEN = "GIG_STATUS_OPEN"
    GIG_STATUS_IN_PROGRESS = "GIG_STATUS_IN_PROGRESS"
    GIG_STATUS_COMPLETED = "GIG_STATUS_COMPLETED"
    GIG_STATUS_CANCELLED = "GIG_STATUS_CANCELLED"
    GIG_STATUS_DISPUTED = "GIG_STATUS_DISPUTED"


class GigModel(Base):
    """Minimal gigs table used by portfolio badge verification.

    The full gig feature (separate issue) will add columns via ALTER TABLE migration.
    """

    __tablename__ = "gigs"

    id: str = Column(  # type: ignore[assignment]
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    status: str = Column(  # type: ignore[assignment]
        Enum(GigStatus, name="gig_status"),
        nullable=False,
        default=GigStatus.GIG_STATUS_DRAFT,
    )
    created_at: datetime = Column(  # type: ignore[assignment]
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: datetime = Column(  # type: ignore[assignment]
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class PortfolioItemModel(Base):
    """Portfolio items table."""

    __tablename__ = "portfolio_items"

    id: str = Column(  # type: ignore[assignment]
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: str = Column(  # type: ignore[assignment]
        String(36),
        nullable=False,
        index=True,
    )
    title: str = Column(String(255), nullable=False)  # type: ignore[assignment]
    description: str = Column(Text, nullable=False, default="")  # type: ignore[assignment]
    file_keys: list = Column(JSON, nullable=False, default=list)  # type: ignore[assignment]
    external_url: str = Column(String(2048), nullable=False, default="")  # type: ignore[assignment]
    tags: list = Column(JSON, nullable=False, default=list)  # type: ignore[assignment]
    # Soft reference to a completed gig — no FK constraint (gig feature is separate)
    verified_gig_id: str | None = Column(  # type: ignore[assignment]
        String(36),
        nullable=True,
        default=None,
    )
    created_at: datetime = Column(  # type: ignore[assignment]
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: datetime = Column(  # type: ignore[assignment]
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_portfolio_items_user_id", "user_id"),
        Index("idx_portfolio_items_created_at", "created_at"),
    )
