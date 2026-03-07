"""
models.py — SQLAlchemy ORM models.
Shapes are driven by the proto definitions in packages/schema/proto/api/v1/.

Notes:
- `id` uses plain String (not postgresql.UUID) so the model works with both
  PostgreSQL (production) and SQLite (tests). The Alembic migration creates the
  column as UUID in PostgreSQL.
- `skills`, `tags`, `required_skills` use JSON (not postgresql.ARRAY) for the same
  cross-dialect reason. In PostgreSQL JSON maps to JSONB; in SQLite it's stored as text.
  The Alembic migration uses TEXT[] for the real PostgreSQL columns.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class GigModel(Base):
    __tablename__ = "gigs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    freelancer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Stored as string (wei for ETH, smallest unit for USDC) to avoid float errors
    total_amount: Mapped[str] = mapped_column(Text, nullable=False)
    # "ETH" or "USDC" — mirrors Currency proto enum names
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="ETH")
    token_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "DRAFT", "OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED", "DISPUTED"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    # JSON works in both PostgreSQL and SQLite (test env)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    required_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    milestones: Mapped[list["MilestoneModel"]] = relationship(
        "MilestoneModel",
        back_populates="gig",
        cascade="all, delete-orphan",
        order_by="MilestoneModel.order",
    )


class MilestoneModel(Base):
    __tablename__ = "milestones"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    gig_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gigs.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Acceptance criteria in markdown — fed to AI reviewer
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    # Amount in wei/smallest unit as string
    amount: Mapped[str] = mapped_column(Text, nullable=False)
    # 1-indexed position within the gig
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # "PENDING", "IN_PROGRESS", "SUBMITTED", "APPROVED", "DISPUTED", "RESOLVED"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    revision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    gig: Mapped["GigModel"] = relationship("GigModel", back_populates="milestones")
