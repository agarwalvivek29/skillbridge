"""
domain/review.py — Business logic for processing OpenReview verdicts.

Called by the GitHub webhook handler when the openreview bot posts a PR review.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.models import (
    GigModel,
    MilestoneModel,
    NotificationModel,
    ReviewReportModel,
    SubmissionModel,
)

logger = logging.getLogger(__name__)

_NOTIFICATION_TYPE_REVIEW_COMPLETE = "NOTIFICATION_TYPE_REVIEW_COMPLETE"


async def process_openreview_verdict(
    db: AsyncSession,
    pr_url: str,
    state: str,
    review_body: str,
) -> None:
    """
    Process a PR review verdict posted by the openreview bot.

    Finds the most recent submission whose repo_url matches pr_url, then:
    - state == "APPROVED"          → submission APPROVED, milestone APPROVED,
                                     ReviewReport(PASS, 100)
    - state == "CHANGES_REQUESTED" → submission REJECTED, milestone REVISION_REQUESTED,
                                     ReviewReport(FAIL, 0)

    Both cases create a notification for the gig's client and freelancer.
    No-ops for any other state value.
    """
    if state not in ("approved", "changes_requested"):
        logger.info("openreview webhook state=%s — ignored", state)
        return

    # Find most recent submission for this PR URL
    result = await db.execute(
        select(SubmissionModel)
        .where(SubmissionModel.repo_url == pr_url)
        .order_by(SubmissionModel.revision_number.desc())
    )
    submission = result.scalars().first()
    if submission is None:
        logger.warning("openreview webhook: no submission found for pr_url=%s", pr_url)
        return

    if submission.status in ("APPROVED", "REJECTED"):
        logger.info(
            "openreview webhook: submission_id=%s already in terminal status %s — skipping",
            submission.id,
            submission.status,
        )
        return

    milestone_result = await db.execute(
        select(MilestoneModel).where(MilestoneModel.id == submission.milestone_id)
    )
    milestone = milestone_result.scalar_one_or_none()
    if milestone is None:
        logger.warning(
            "openreview webhook: milestone %s not found for submission %s",
            submission.milestone_id,
            submission.id,
        )
        return

    gig_result = await db.execute(
        select(GigModel).where(GigModel.id == milestone.gig_id)
    )
    gig = gig_result.scalar_one_or_none()
    if gig is None:
        logger.warning(
            "openreview webhook: gig %s not found for milestone %s",
            milestone.gig_id,
            milestone.id,
        )
        return

    # Idempotency: if a ReviewReport already exists for this submission, skip
    existing = await db.execute(
        select(ReviewReportModel).where(
            ReviewReportModel.submission_id == submission.id
        )
    )
    if existing.scalar_one_or_none() is not None:
        logger.info(
            "openreview webhook: ReviewReport already exists for submission_id=%s — skipping duplicate",
            submission.id,
        )
        return

    if state == "approved":
        submission.status = "APPROVED"
        milestone.status = "APPROVED"
        verdict = "PASS"
        score = 100
    else:  # changes_requested
        submission.status = "REJECTED"
        milestone.status = "REVISION_REQUESTED"
        verdict = "FAIL"
        score = 0

    await db.flush()

    # Write ReviewReport
    report = ReviewReportModel(
        submission_id=submission.id,
        verdict=verdict,
        score=score,
        body=review_body or "",
        model_version="openreview",
    )
    db.add(report)
    await db.flush()

    # Notify client and freelancer
    payload = json.dumps(
        {
            "submission_id": submission.id,
            "milestone_id": milestone.id,
            "gig_id": gig.id,
            "verdict": verdict,
            "score": score,
        }
    )
    for user_id in {gig.client_id, gig.freelancer_id}:
        if user_id:
            db.add(
                NotificationModel(
                    user_id=user_id,
                    type=_NOTIFICATION_TYPE_REVIEW_COMPLETE,
                    payload_json=payload,
                )
            )
    await db.flush()

    logger.info(
        "openreview verdict processed submission_id=%s verdict=%s score=%d",
        submission.id,
        verdict,
        score,
    )
