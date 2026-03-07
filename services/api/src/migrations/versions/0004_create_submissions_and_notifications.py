"""create submissions and notifications tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "milestone_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("milestones.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "freelancer_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("repo_url", sa.Text, nullable=True),
        sa.Column(
            "file_keys",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("revision_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "previous_submission_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("submissions.id"),
            nullable=True,
        ),
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

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Index for fast lookup of notifications per user
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    # Index for fast lookup of submissions per milestone
    op.create_index("ix_submissions_milestone_id", "submissions", ["milestone_id"])


def downgrade() -> None:
    op.drop_index("ix_submissions_milestone_id", table_name="submissions")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("submissions")
