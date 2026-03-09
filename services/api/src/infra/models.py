"""
models.py — SQLAlchemy ORM models.
Shapes are driven by the proto definitions in packages/schema/proto/api/v1/.

Notes:
- `id` uses plain String (not postgresql.UUID) so the model works with both
  PostgreSQL (production) and SQLite (tests). The Alembic migration creates the
  column as UUID in PostgreSQL.
- `skills`, `tags`, `required_skills`, `file_keys` use JSON (not postgresql.ARRAY) for
  the same cross-dialect reason. In PostgreSQL JSON maps to JSONB; in SQLite it's stored
  as text. The Alembic migration uses TEXT[] for the real PostgreSQL columns.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
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
    # "PENDING", "IN_PROGRESS", "SUBMITTED", "APPROVED", "DISPUTED", "RESOLVED", "PAID", "REVISION_REQUESTED"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    revision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # tx_hash of the completeMilestone() call after client confirms fund release
    release_tx_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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


class PortfolioItemModel(Base):
    __tablename__ = "portfolio_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON type works in both PostgreSQL and SQLite (test env)
    file_keys: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # If set and the linked gig is COMPLETED, a "Verified Delivery" badge is shown
    verified_gig_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gigs.id", ondelete="SET NULL"), nullable=True
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


class SubmissionModel(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    milestone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("milestones.id", ondelete="CASCADE"), nullable=False
    )
    freelancer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    repo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON works in both PostgreSQL and SQLite (test env); migration uses TEXT[]
    file_keys: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # "PENDING", "UNDER_REVIEW", "APPROVED", "REJECTED"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    # 1-indexed; increments with each resubmission
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Points to the prior submission for resubmissions; null for first submission
    previous_submission_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("submissions.id"), nullable=True
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


class ProposalModel(Base):
    __tablename__ = "proposals"
    __table_args__ = (
        UniqueConstraint("gig_id", "freelancer_id", name="uq_proposal_gig_freelancer"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    gig_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gigs.id", ondelete="CASCADE"), nullable=False
    )
    freelancer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    cover_letter: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_days: Mapped[int] = mapped_column(Integer, nullable=False)
    # "PENDING", "ACCEPTED", "REJECTED", "WITHDRAWN"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ReviewReportModel(Base):
    __tablename__ = "review_reports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    submission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    # "PASS" or "FAIL"
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    # v1: binary — 100 = PASS (approved), 0 = FAIL (changes_requested)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    # Raw review body text from the openreview bot PR review
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="openreview"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EscrowContractModel(Base):
    __tablename__ = "escrow_contracts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    gig_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gigs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # On-chain contract address of the deployed GigEscrow
    contract_address: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class NotificationModel(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    # NotificationType enum name, e.g. "NOTIFICATION_TYPE_PROPOSAL_RECEIVED"
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    # Context-specific JSON payload for rendering notification message
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # null = unread
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DisputeModel(Base):
    __tablename__ = "disputes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    milestone_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("milestones.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    gig_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gigs.id", ondelete="CASCADE"), nullable=False
    )
    raised_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # "OPEN", "ARBITRATION", "RESOLVED"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    ai_evidence_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    freelancer_split_amount: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_tx_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discussion_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
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

    messages: Mapped[list["DisputeMessageModel"]] = relationship(
        "DisputeMessageModel",
        back_populates="dispute",
        cascade="all, delete-orphan",
        order_by="DisputeMessageModel.created_at",
    )


class DisputeMessageModel(Base):
    __tablename__ = "dispute_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dispute_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("disputes.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    dispute: Mapped["DisputeModel"] = relationship(
        "DisputeModel", back_populates="messages"
    )
