"""create gigs and milestones tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gigs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("freelancer_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("total_amount", sa.Text, nullable=False),
        sa.Column(
            "currency",
            sa.String(32),
            nullable=False,
            server_default="CURRENCY_ETH",
        ),
        sa.Column("token_address", sa.Text, nullable=False, server_default=""),
        sa.Column("contract_address", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="GIG_STATUS_DRAFT",
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "required_skills",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_gigs_client_id", "gigs", ["client_id"])
    op.create_index("ix_gigs_status", "gigs", ["status"])

    op.create_table(
        "milestones",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "gig_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("gigs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("acceptance_criteria", sa.Text, nullable=False),
        sa.Column("amount", sa.Text, nullable=False),
        sa.Column('"order"', sa.Integer, nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="MILESTONE_STATUS_PENDING",
        ),
        sa.Column("contract_index", sa.Integer, nullable=False, server_default="-1"),
        sa.Column("revision_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_milestones_gig_id", "milestones", ["gig_id"])


def downgrade() -> None:
    op.drop_index("ix_milestones_gig_id", "milestones")
    op.drop_table("milestones")
    op.drop_index("ix_gigs_status", "gigs")
    op.drop_index("ix_gigs_client_id", "gigs")
    op.drop_table("gigs")
