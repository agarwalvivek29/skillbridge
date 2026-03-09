"""
infra/email.py — Email delivery via SendGrid.

Best-effort: failures are logged but never block notification creation.
Disabled when SENDGRID_API_KEY is empty.
"""

from __future__ import annotations

import logging

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

# Mapping from notification type to human-readable subject lines
_SUBJECT_MAP: dict[str, str] = {
    "NOTIFICATION_TYPE_GIG_FUNDED": "Your gig has been funded",
    "NOTIFICATION_TYPE_GIG_CANCELLED": "A gig has been cancelled",
    "NOTIFICATION_TYPE_GIG_COMPLETED": "Gig completed",
    "NOTIFICATION_TYPE_PROPOSAL_RECEIVED": "New proposal received",
    "NOTIFICATION_TYPE_PROPOSAL_ACCEPTED": "Your proposal was accepted",
    "NOTIFICATION_TYPE_PROPOSAL_REJECTED": "Your proposal was not selected",
    "NOTIFICATION_TYPE_SUBMISSION_RECEIVED": "New submission received",
    "NOTIFICATION_TYPE_REVISION_REQUESTED": "Revision requested on your submission",
    "NOTIFICATION_TYPE_MILESTONE_APPROVED": "Milestone approved",
    "NOTIFICATION_TYPE_FUNDS_RELEASED": "Funds released to your wallet",
    "NOTIFICATION_TYPE_REVIEW_COMPLETE": "AI review completed",
    "NOTIFICATION_TYPE_DISPUTE_RAISED": "A dispute has been raised",
    "NOTIFICATION_TYPE_DISPUTE_RESOLVED": "Dispute resolved",
    "NOTIFICATION_TYPE_REVIEW_RECEIVED": "You received a new review",
}


def is_email_enabled() -> bool:
    """Return True if SendGrid is configured."""
    return bool(settings.sendgrid_api_key)


async def send_notification_email(
    to_email: str,
    notification_type: str,
    payload: dict,
) -> None:
    """
    Send a notification email via SendGrid v3 Mail Send API.

    Best-effort: logs errors but never raises.
    """
    if not is_email_enabled():
        return

    subject = _SUBJECT_MAP.get(notification_type, "SkillBridge Notification")

    # Build plain text body from payload
    body_lines = [subject, "", "Details:"]
    for key, value in payload.items():
        body_lines.append(f"  {key}: {value}")
    body_lines.append("")
    body_lines.append("— SkillBridge")
    plain_text = "\n".join(body_lines)

    # Minimal HTML
    html_body = (
        f"<h2>{subject}</h2>"
        f"<pre>{plain_text}</pre>"
        f"<p><small>You can manage your notification preferences in your SkillBridge settings.</small></p>"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {settings.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": settings.sendgrid_from_email},
                    "subject": subject,
                    "content": [
                        {"type": "text/plain", "value": plain_text},
                        {"type": "text/html", "value": html_body},
                    ],
                },
            )
            if response.status_code >= 400:
                logger.warning(
                    "sendgrid email failed status=%d body=%s to=%s type=%s",
                    response.status_code,
                    response.text[:200],
                    to_email,
                    notification_type,
                )
            else:
                logger.info(
                    "email sent to=%s type=%s",
                    to_email,
                    notification_type,
                )
    except Exception:
        logger.exception(
            "sendgrid email error to=%s type=%s", to_email, notification_type
        )
