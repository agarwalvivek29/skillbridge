"""create review_reports table

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "review_reports",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "submission_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("verdict", sa.String(32), nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "model_version",
            sa.String(64),
            nullable=False,
            server_default="openreview",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_review_reports_submission_id", "review_reports", ["submission_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_review_reports_submission_id", table_name="review_reports")
    op.drop_table("review_reports")
