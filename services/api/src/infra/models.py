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


class PortfolioItemModel(Base):
    """
    ORM model for portfolio_items.
    Driven by packages/schema/proto/api/v1/portfolio.proto (PortfolioItem).

    Notes:
    - `file_keys` and `tags` use JSON (not postgresql.ARRAY) so the model works
      with both PostgreSQL (production) and SQLite (tests). Alembic migration
      uses TEXT[] for the real PostgreSQL columns.
    - `verified_gig_id` is a soft reference to a future `gigs` table.
      No FK enforced in v1 — the `gigs` table does not exist yet.
    - `is_verified` is never stored; it is computed at read time.
    """

    __tablename__ = "portfolio_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON works in both PostgreSQL and SQLite test env
    file_keys: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Soft reference to a gig; no FK constraint in v1
    verified_gig_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class GigModel(Base):
    """
    ORM model for gigs.
    Driven by packages/schema/proto/api/v1/gig.proto (Gig).

    Notes:
    - `tags` and `required_skills` use JSON for cross-dialect compatibility
      (PostgreSQL + SQLite). Alembic migration uses TEXT[] in PostgreSQL.
    - `total_amount` stores the raw string from the client (wei for ETH, smallest
      unit for USDC). No numeric parsing in the ORM layer.
    - `client_id` / `freelancer_id` are string FKs referencing users.id.
    """

    __tablename__ = "gigs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    freelancer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    total_amount: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(32), nullable=False, default="CURRENCY_ETH"
    )
    token_address: Mapped[str] = mapped_column(Text, nullable=False, default="")
    contract_address: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="GIG_STATUS_DRAFT"
    )
    # JSON works in both PostgreSQL and SQLite test env
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
    """
    ORM model for milestones.
    Driven by packages/schema/proto/api/v1/milestone.proto (Milestone).

    Notes:
    - `amount` stores the raw string (wei / smallest unit).
    - `acceptance_criteria` stores markdown text fed to the AI reviewer (Issue #7).
    - `contract_index` is -1 until the escrow contract is deployed (Issue #4).
    """

    __tablename__ = "milestones"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    gig_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gigs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[str] = mapped_column(Text, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="MILESTONE_STATUS_PENDING"
    )
    contract_index: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    revision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    due_date: Mapped[datetime | None] = mapped_column(
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

    gig: Mapped["GigModel"] = relationship("GigModel", back_populates="milestones")
