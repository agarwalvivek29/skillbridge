"""Create disputes and dispute_messages tables.

Revision ID: 0008
Revises: 0007
"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "disputes",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "milestone_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("milestones.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "gig_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("gigs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "raised_by_user_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("ai_evidence_summary", sa.Text(), nullable=True),
        sa.Column("resolution", sa.String(32), nullable=True),
        sa.Column("freelancer_split_amount", sa.Text(), nullable=True),
        sa.Column("resolution_tx_hash", sa.Text(), nullable=True),
        sa.Column("discussion_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("milestone_id", name="uq_dispute_milestone"),
    )

    op.create_table(
        "dispute_messages",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "dispute_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("disputes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("dispute_messages")
    op.drop_table("disputes")
