"""
domain/submission.py — Business logic for work submission.
No FastAPI imports. All side-effect-free helpers + DB-taking functions.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.celery_client import enqueue_review
from src.infra.models import (
    GigModel,
    MilestoneModel,
    NotificationModel,
    SubmissionModel,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SUBMITTABLE_MILESTONE_STATUSES = {"PENDING", "IN_PROGRESS", "REVISION_REQUESTED"}
_NOTIFICATION_TYPE_SUBMISSION_RECEIVED = "NOTIFICATION_TYPE_SUBMISSION_RECEIVED"

# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class SubmissionValidationError(ValueError):
    """Raised when submission data fails business-rule validation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Domain functions
# ---------------------------------------------------------------------------


async def create_submission(
    db: AsyncSession,
    freelancer_id: str,
    milestone_id: str,
    repo_url: Optional[str],
    file_keys: list[str],
    notes: str,
    previous_submission_id: Optional[str],
) -> SubmissionModel:
    """
    Create a work submission for a milestone.

    Validates:
    - Milestone exists
    - Gig has an assigned freelancer and caller is that freelancer
    - Milestone is in a submittable status (PENDING, IN_PROGRESS, REVISION_REQUESTED)
    - At least one of repo_url or file_keys must be provided
    - previous_submission_id is required when milestone is REVISION_REQUESTED

    Side effects:
    - Milestone status: → SUBMITTED → UNDER_REVIEW
    - Milestone revision_count incremented
    - Celery task review.enqueue dispatched
    - Notification created for client (NOTIFICATION_TYPE_SUBMISSION_RECEIVED)

    Returns the created SubmissionModel.
    """
    # Fetch milestone and its gig
    milestone_result = await db.execute(
        select(MilestoneModel).where(MilestoneModel.id == milestone_id)
    )
    milestone = milestone_result.scalar_one_or_none()
    if milestone is None:
        raise SubmissionValidationError(
            "MILESTONE_NOT_FOUND", f"Milestone {milestone_id} not found"
        )

    gig_result = await db.execute(
        select(GigModel).where(GigModel.id == milestone.gig_id)
    )
    gig = gig_result.scalar_one_or_none()
    if gig is None:
        raise SubmissionValidationError(
            "GIG_NOT_FOUND", f"Gig for milestone {milestone_id} not found"
        )

    # Gig must have an assigned freelancer
    if gig.freelancer_id is None:
        raise SubmissionValidationError(
            "GIG_NOT_IN_PROGRESS",
            "No freelancer is assigned to this gig; submission not allowed",
        )

    # Caller must be the assigned freelancer
    if gig.freelancer_id != freelancer_id:
        raise SubmissionValidationError(
            "FORBIDDEN",
            "Only the assigned freelancer may submit work on this gig",
        )

    # Milestone must be in a submittable status
    if milestone.status not in _SUBMITTABLE_MILESTONE_STATUSES:
        raise SubmissionValidationError(
            "MILESTONE_NOT_SUBMITTABLE",
            f"Milestone cannot accept a submission in status {milestone.status}",
        )

    # At least one deliverable must be provided
    if not repo_url and not file_keys:
        raise SubmissionValidationError(
            "NO_DELIVERABLE",
            "At least one of repo_url or file_keys must be provided",
        )

    # Compute revision_number
    count_result = await db.execute(
        select(func.count())
        .select_from(SubmissionModel)
        .where(SubmissionModel.milestone_id == milestone_id)
    )
    existing_count = count_result.scalar_one()
    revision_number = existing_count + 1

    # For resubmissions, validate previous_submission_id
    if milestone.status == "REVISION_REQUESTED":
        if not previous_submission_id:
            raise SubmissionValidationError(
                "PREVIOUS_SUBMISSION_REQUIRED",
                "previous_submission_id is required when resubmitting after a revision request",
            )
        prev_result = await db.execute(
            select(SubmissionModel).where(
                SubmissionModel.id == previous_submission_id,
                SubmissionModel.milestone_id == milestone_id,
            )
        )
        if prev_result.scalar_one_or_none() is None:
            raise SubmissionValidationError(
                "PREVIOUS_SUBMISSION_NOT_FOUND",
                f"previous_submission_id {previous_submission_id} not found for this milestone",
            )

    # Create submission record
    submission = SubmissionModel(
        milestone_id=milestone_id,
        freelancer_id=freelancer_id,
        repo_url=repo_url or None,
        file_keys=file_keys or [],
        notes=notes,
        status="PENDING",
        revision_number=revision_number,
        previous_submission_id=previous_submission_id or None,
    )
    db.add(submission)
    await db.flush()  # populate submission.id

    # Transition milestone: → SUBMITTED
    milestone.status = "SUBMITTED"
    milestone.revision_count = milestone.revision_count + 1
    await db.flush()

    # Enqueue review job (best-effort; Redis unavailability is logged, not fatal)
    enqueue_review(submission.id)

    # Transition submission and milestone: → UNDER_REVIEW
    submission.status = "UNDER_REVIEW"
    milestone.status = "UNDER_REVIEW"
    await db.flush()

    # Notify client
    payload = json.dumps(
        {
            "submission_id": submission.id,
            "milestone_id": milestone_id,
            "gig_id": gig.id,
            "revision_number": revision_number,
        }
    )
    notification = NotificationModel(
        user_id=gig.client_id,
        type=_NOTIFICATION_TYPE_SUBMISSION_RECEIVED,
        payload_json=payload,
    )
    db.add(notification)
    await db.flush()

    logger.info(
        "submission created submission_id=%s milestone_id=%s revision=%d",
        submission.id,
        milestone_id,
        revision_number,
    )

    # Re-fetch to avoid lazy-load issues with server-default timestamps
    result = await db.execute(
        select(SubmissionModel).where(SubmissionModel.id == submission.id)
    )
    return result.scalar_one()


async def get_submission(
    db: AsyncSession, submission_id: str
) -> SubmissionModel | None:
    """Return a single submission, or None if not found."""
    result = await db.execute(
        select(SubmissionModel).where(SubmissionModel.id == submission_id)
    )
    return result.scalar_one_or_none()


async def list_submissions(
    db: AsyncSession, milestone_id: str
) -> list[SubmissionModel]:
    """Return all submissions for a milestone ordered by revision_number ascending."""
    result = await db.execute(
        select(SubmissionModel)
        .where(SubmissionModel.milestone_id == milestone_id)
        .order_by(SubmissionModel.revision_number.asc())
    )
    return list(result.scalars().all())
