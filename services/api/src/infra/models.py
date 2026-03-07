"""
models.py — SQLAlchemy ORM models.
Shapes are driven by the proto definitions in packages/schema/proto/api/v1/.

Notes:
- `id` uses plain String (not postgresql.UUID) so the model works with both
  PostgreSQL (production) and SQLite (tests). The Alembic migration creates the
  column as UUID in PostgreSQL.
- `skills` uses JSON (not postgresql.ARRAY) for the same cross-dialect reason.
  In PostgreSQL JSON maps to JSONB; in SQLite it's stored as text.
  The Alembic migration uses TEXT[] for the real PostgreSQL column.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    wallet_address: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="USER_ROLE_FREELANCER"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="USER_STATUS_ACTIVE"
    )
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON type works in both PostgreSQL and SQLite (test env)
    skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    hourly_rate_wei: Mapped[str] = mapped_column(Text, nullable=False, default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AuthNonceModel(Base):
    __tablename__ = "auth_nonces"

    wallet_address: Mapped[str] = mapped_column(Text, primary_key=True)
    nonce: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
