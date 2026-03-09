"""
domain/dispute.py — Business logic for dispute resolution.

Implements:
- raise_dispute: CLIENT or FREELANCER raises a dispute on a milestone
- get_dispute: fetch dispute with messages
- get_dispute_by_milestone: fetch active dispute for a milestone
- post_dispute_message: add a message during discussion window
- resolve_dispute: ADMIN resolves the dispute (records on-chain tx)
- escalate_open_disputes: background job to escalate past-deadline disputes
- generate_ai_evidence: async AI evidence generation

No FastAPI imports. All domain logic lives here; routers stay thin.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infra.models import (
    DisputeMessageModel,
    DisputeModel,
    GigModel,
    MilestoneModel,
    NotificationModel,
    ReviewReportModel,
    SubmissionModel,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Milestone statuses that allow raising a dispute
_DISPUTABLE_STATUSES = {"SUBMITTED", "UNDER_REVIEW"}

DISCUSSION_WINDOW_DAYS = 3

_NOTIFICATION_TYPE_DISPUTE_RAISED = "NOTIFICATION_TYPE_DISPUTE_RAISED"
_NOTIFICATION_TYPE_DISPUTE_RESOLVED = "NOTIFICATION_TYPE_DISPUTE_RESOLVED"

_VALID_RESOLUTIONS = {
    "DISPUTE_RESOLUTION_PAY_FREELANCER",
    "DISPUTE_RESOLUTION_REFUND_CLIENT",
    "DISPUTE_RESOLUTION_SPLIT",
}

# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class DisputeError(ValueError):
    """Raised when a dispute operation fails a business rule."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fetch_gig_for_dispute(
    db: AsyncSession,
    gig_id: str,
    user_id: str,
) -> GigModel:
    """Load gig and verify caller is a party (client or freelancer)."""
    result = await db.execute(select(GigModel).where(GigModel.id == gig_id))
    gig = result.scalar_one_or_none()
    if gig is None:
        raise DisputeError("GIG_NOT_FOUND", f"Gig {gig_id} not found")
    if gig.client_id != user_id and gig.freelancer_id != user_id:
        raise DisputeError(
            "FORBIDDEN",
            "Only the gig's client or assigned freelancer may perform this action",
        )
    return gig


def _notify(
    db: AsyncSession,
    user_id: str,
    notification_type: str,
    payload: dict,
) -> None:
    """Add a notification row (does not flush)."""
    db.add(
        NotificationModel(
            user_id=user_id,
            type=notification_type,
            payload_json=json.dumps(payload),
        )
    )


# ---------------------------------------------------------------------------
# Domain functions
# ---------------------------------------------------------------------------


async def raise_dispute(
    db: AsyncSession,
    user_id: str,
    milestone_id: str,
    reason: str,
) -> DisputeModel:
    """
    Raise a dispute on a milestone.

    Validates:
    - Milestone exists and is in SUBMITTED or UNDER_REVIEW status
    - Caller is the gig's client or assigned freelancer
    - No existing dispute for this milestone

    Side effects:
    - Creates DisputeModel with status=OPEN
    - Sets milestone.status = DISPUTED
    - Creates DISPUTE_RAISED notifications for both parties
    """
    milestone_result = await db.execute(
        select(MilestoneModel).where(MilestoneModel.id == milestone_id)
    )
    milestone = milestone_result.scalar_one_or_none()
    if milestone is None:
        raise DisputeError("MILESTONE_NOT_FOUND", f"Milestone {milestone_id} not found")

    if milestone.status not in _DISPUTABLE_STATUSES:
        raise DisputeError(
            "MILESTONE_NOT_DISPUTABLE",
            f"Cannot dispute a milestone in status {milestone.status}",
        )

    gig = await _fetch_gig_for_dispute(db, milestone.gig_id, user_id)

    # Check for existing dispute on this milestone
    existing_result = await db.execute(
        select(DisputeModel).where(DisputeModel.milestone_id == milestone_id)
    )
    if existing_result.scalar_one_or_none() is not None:
        raise DisputeError(
            "DISPUTE_ALREADY_EXISTS",
            "A dispute already exists for this milestone",
        )

    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=DISCUSSION_WINDOW_DAYS)

    dispute = DisputeModel(
        milestone_id=milestone_id,
        gig_id=gig.id,
        raised_by_user_id=user_id,
        reason=reason,
        status="OPEN",
        discussion_deadline=deadline,
    )
    db.add(dispute)
    await db.flush()

    # Transition milestone status
    milestone.status = "DISPUTED"
    await db.flush()

    # Notify both parties
    payload = {
        "dispute_id": dispute.id,
        "milestone_id": milestone_id,
        "gig_id": gig.id,
        "raised_by": user_id,
        "reason": reason,
    }
    for uid in {gig.client_id, gig.freelancer_id}:
        if uid:
            _notify(db, uid, _NOTIFICATION_TYPE_DISPUTE_RAISED, payload)
    await db.flush()

    logger.info(
        "dispute raised dispute_id=%s milestone_id=%s by user_id=%s",
        dispute.id,
        milestone_id,
        user_id,
    )

    # Re-fetch to get server-default timestamps + eager-load messages
    result = await db.execute(
        select(DisputeModel)
        .where(DisputeModel.id == dispute.id)
        .options(selectinload(DisputeModel.messages))
    )
    return result.scalar_one()


async def get_dispute(
    db: AsyncSession,
    dispute_id: str,
) -> DisputeModel | None:
    """Fetch a dispute with its messages eagerly loaded."""
    result = await db.execute(
        select(DisputeModel)
        .where(DisputeModel.id == dispute_id)
        .options(selectinload(DisputeModel.messages))
    )
    return result.scalar_one_or_none()


async def get_dispute_by_milestone(
    db: AsyncSession,
    milestone_id: str,
) -> DisputeModel | None:
    """Fetch the active dispute for a milestone, with messages."""
    result = await db.execute(
        select(DisputeModel)
        .where(DisputeModel.milestone_id == milestone_id)
        .options(selectinload(DisputeModel.messages))
    )
    return result.scalar_one_or_none()


async def post_dispute_message(
    db: AsyncSession,
    user_id: str,
    dispute_id: str,
    content: str,
) -> DisputeMessageModel:
    """
    Post a message in a dispute discussion.

    Validates:
    - Dispute exists and is OPEN
    - Current time is before discussion_deadline
    - Caller is the gig's client or assigned freelancer
    """
    dispute_result = await db.execute(
        select(DisputeModel).where(DisputeModel.id == dispute_id)
    )
    dispute = dispute_result.scalar_one_or_none()
    if dispute is None:
        raise DisputeError("DISPUTE_NOT_FOUND", f"Dispute {dispute_id} not found")

    if dispute.status != "OPEN":
        raise DisputeError(
            "DISPUTE_NOT_OPEN",
            f"Cannot post messages to a dispute in status {dispute.status}",
        )

    now = datetime.now(timezone.utc)
    if now >= dispute.discussion_deadline.replace(tzinfo=timezone.utc):
        raise DisputeError(
            "DISCUSSION_DEADLINE_PASSED",
            "The discussion deadline has passed; no new messages allowed",
        )

    # Verify caller is a party to the gig
    await _fetch_gig_for_dispute(db, dispute.gig_id, user_id)

    message = DisputeMessageModel(
        dispute_id=dispute_id,
        user_id=user_id,
        content=content,
    )
    db.add(message)
    await db.flush()

    logger.info(
        "dispute message posted message_id=%s dispute_id=%s by user_id=%s",
        message.id,
        dispute_id,
        user_id,
    )

    # Re-fetch to get server-default timestamps
    result = await db.execute(
        select(DisputeMessageModel).where(DisputeMessageModel.id == message.id)
    )
    return result.scalar_one()


async def resolve_dispute(
    db: AsyncSession,
    dispute_id: str,
    resolution: str,
    freelancer_split_amount: Optional[str],
    tx_hash: str,
) -> DisputeModel:
    """
    Resolve a dispute (ADMIN only — role check done in router).

    Validates:
    - Dispute exists and is in OPEN or ARBITRATION status
    - Resolution is a valid DisputeResolution value
    - freelancer_split_amount is required for SPLIT resolution

    Side effects:
    - dispute.status → RESOLVED
    - Records resolution, tx_hash, resolved_at
    - Milestone status → RESOLVED
    - Creates DISPUTE_RESOLVED notifications for both parties
    """
    dispute_result = await db.execute(
        select(DisputeModel).where(DisputeModel.id == dispute_id)
    )
    dispute = dispute_result.scalar_one_or_none()
    if dispute is None:
        raise DisputeError("DISPUTE_NOT_FOUND", f"Dispute {dispute_id} not found")

    if dispute.status not in ("OPEN", "ARBITRATION"):
        raise DisputeError(
            "DISPUTE_NOT_RESOLVABLE",
            f"Cannot resolve a dispute in status {dispute.status}",
        )

    if resolution not in _VALID_RESOLUTIONS:
        raise DisputeError(
            "INVALID_RESOLUTION",
            f"Resolution must be one of: {', '.join(sorted(_VALID_RESOLUTIONS))}",
        )

    if resolution == "DISPUTE_RESOLUTION_SPLIT" and not freelancer_split_amount:
        raise DisputeError(
            "SPLIT_AMOUNT_REQUIRED",
            "freelancer_split_amount is required for SPLIT resolution",
        )

    now = datetime.now(timezone.utc)
    dispute.status = "RESOLVED"
    dispute.resolution = resolution
    dispute.freelancer_split_amount = freelancer_split_amount
    dispute.resolution_tx_hash = tx_hash
    dispute.resolved_at = now
    await db.flush()

    # Transition milestone status
    milestone_result = await db.execute(
        select(MilestoneModel).where(MilestoneModel.id == dispute.milestone_id)
    )
    milestone = milestone_result.scalar_one_or_none()
    if milestone is not None:
        milestone.status = "RESOLVED"
        await db.flush()

    # Notify both parties
    gig_result = await db.execute(select(GigModel).where(GigModel.id == dispute.gig_id))
    gig = gig_result.scalar_one_or_none()
    if gig is not None:
        payload = {
            "dispute_id": dispute.id,
            "milestone_id": dispute.milestone_id,
            "gig_id": dispute.gig_id,
            "resolution": resolution,
            "tx_hash": tx_hash,
        }
        for uid in {gig.client_id, gig.freelancer_id}:
            if uid:
                _notify(db, uid, _NOTIFICATION_TYPE_DISPUTE_RESOLVED, payload)
        await db.flush()

    logger.info(
        "dispute resolved dispute_id=%s resolution=%s tx_hash=%s",
        dispute.id,
        resolution,
        tx_hash,
    )

    # Re-fetch with eager-loaded messages
    result = await db.execute(
        select(DisputeModel)
        .where(DisputeModel.id == dispute.id)
        .options(selectinload(DisputeModel.messages))
    )
    return result.scalar_one()


async def escalate_open_disputes(db: AsyncSession) -> int:
    """
    Background job: escalate OPEN disputes past their discussion_deadline to ARBITRATION.

    Returns the number of disputes escalated.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(DisputeModel).where(
            DisputeModel.status == "OPEN",
            DisputeModel.discussion_deadline <= now,
        )
    )
    disputes = list(result.scalars().all())

    for dispute in disputes:
        dispute.status = "ARBITRATION"

    if disputes:
        await db.flush()
        logger.info("escalated %d disputes to ARBITRATION", len(disputes))

    return len(disputes)


async def generate_ai_evidence(
    db: AsyncSession,
    dispute_id: str,
) -> None:
    """
    Generate AI evidence summary for a dispute.

    Logic:
    - If the latest submission has a repo_url, copy the ReviewReport body
    - If file-only, call Claude with acceptance_criteria + submission notes
    - Updates dispute.ai_evidence_summary
    """
    dispute_result = await db.execute(
        select(DisputeModel).where(DisputeModel.id == dispute_id)
    )
    dispute = dispute_result.scalar_one_or_none()
    if dispute is None:
        logger.warning("generate_ai_evidence: dispute %s not found", dispute_id)
        return

    # Find latest submission for this milestone
    submission_result = await db.execute(
        select(SubmissionModel)
        .where(SubmissionModel.milestone_id == dispute.milestone_id)
        .order_by(SubmissionModel.revision_number.desc())
    )
    submission = submission_result.scalars().first()
    if submission is None:
        logger.warning(
            "generate_ai_evidence: no submissions for milestone %s",
            dispute.milestone_id,
        )
        dispute.ai_evidence_summary = "No submissions found for this milestone."
        await db.flush()
        return

    # If submission has a repo_url, look for an existing ReviewReport
    if submission.repo_url:
        report_result = await db.execute(
            select(ReviewReportModel).where(
                ReviewReportModel.submission_id == submission.id
            )
        )
        report = report_result.scalar_one_or_none()
        if report is not None and report.body:
            dispute.ai_evidence_summary = report.body
            await db.flush()
            logger.info(
                "ai_evidence from ReviewReport dispute_id=%s submission_id=%s",
                dispute_id,
                submission.id,
            )
            return

    # File-only or no ReviewReport: call Claude API
    milestone_result = await db.execute(
        select(MilestoneModel).where(MilestoneModel.id == dispute.milestone_id)
    )
    milestone = milestone_result.scalar_one_or_none()
    acceptance_criteria = milestone.acceptance_criteria if milestone else ""

    try:
        summary = await _call_claude_for_evidence(
            acceptance_criteria=acceptance_criteria,
            submission_notes=submission.notes,
            file_keys=submission.file_keys or [],
        )
        dispute.ai_evidence_summary = summary
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "ai_evidence Claude call failed dispute_id=%s error=%s",
            dispute_id,
            exc,
        )
        dispute.ai_evidence_summary = (
            "AI evidence generation failed. Manual review required."
        )

    await db.flush()
    logger.info("ai_evidence generated dispute_id=%s", dispute_id)


async def _call_claude_for_evidence(
    acceptance_criteria: str,
    submission_notes: str,
    file_keys: list[str],
) -> str:
    """Call Claude API to generate an evidence summary. Max 500 tokens."""
    from src.config import settings

    if not getattr(settings, "anthropic_api_key", ""):
        return "AI evidence unavailable: ANTHROPIC_API_KEY not configured."

    import httpx

    prompt = (
        "You are an impartial dispute evidence analyst for a freelance platform. "
        "Analyze whether the freelancer's submission meets the acceptance criteria.\n\n"
        f"## Acceptance Criteria\n{acceptance_criteria}\n\n"
        f"## Submission Notes\n{submission_notes}\n\n"
        f"## Submitted Files\n{', '.join(file_keys) if file_keys else 'None'}\n\n"
        "Provide a concise, factual summary of whether the submission appears to meet "
        "the criteria. Be neutral and evidence-based."
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6-20250514",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
