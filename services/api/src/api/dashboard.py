"""dashboard.py — Client and freelancer dashboard endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import GigStatus, MilestoneStatus, ProposalStatus
from src.infra.database import get_db
from src.infra.models import (
    EscrowContractModel,
    GigModel,
    MilestoneModel,
    NotificationModel,
    ProposalModel,
    ReviewReportModel,
    SubmissionModel,
    UserModel,
)

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])

# ── Response schemas ─────────────────────────────────────────────────────────


class GigMilestoneOut(BaseModel):
    id: str
    gig_id: str
    title: str
    description: str
    amount: str
    currency: str
    status: str
    order: int
    due_date: str | None


class ActiveGigOut(BaseModel):
    id: str
    client_id: str
    client_name: str | None
    client_avatar_url: str | None
    client_wallet_address: str | None
    freelancer_id: str | None
    title: str
    description: str
    category: str | None
    skills: list[str]
    total_amount: str
    currency: str
    status: str
    deadline: str | None
    created_at: str
    milestones: list[GigMilestoneOut]
    proposal_count: int
    escrow_balance: str


class PendingActionOut(BaseModel):
    type: str
    gig_id: str
    gig_title: str
    label: str
    link: str
    created_at: str


class EscrowPerGigOut(BaseModel):
    gig_id: str
    title: str
    amount: str


class EscrowOverviewOut(BaseModel):
    total_locked: str
    per_gig: list[EscrowPerGigOut]


class ActivityEventOut(BaseModel):
    id: str
    type: str
    message: str
    gig_id: str
    created_at: str


class ClientStatsOut(BaseModel):
    total_gigs: int
    active_freelancers: int
    avg_approval_time: str


class ClientDashboardResponse(BaseModel):
    active_gigs: list[ActiveGigOut]
    pending_actions: list[PendingActionOut]
    escrow_overview: EscrowOverviewOut
    recent_activity: list[ActivityEventOut]
    stats: ClientStatsOut


class ActiveMilestoneOut(BaseModel):
    id: str
    gig_id: str
    gig_title: str
    milestone_name: str
    budget: str
    status: str
    deadline: str | None


class ApplicationSummaryOut(BaseModel):
    id: str
    gig_id: str
    gig_title: str
    status: str
    created_at: str


class EarningsDayOut(BaseModel):
    date: str
    amount: str


class EarningsOut(BaseModel):
    total_earned: str
    pending_payment: str
    last_30_days: list[EarningsDayOut]


class RecentReviewOut(BaseModel):
    score: int
    review: str | None
    created_at: str


class ReputationOut(BaseModel):
    score: int
    badge_tier: str
    recent_reviews: list[RecentReviewOut]


class AIReviewOut(BaseModel):
    milestone_name: str
    verdict: str
    score: int
    created_at: str


class FreelancerDashboardResponse(BaseModel):
    active_milestones: list[ActiveMilestoneOut]
    applications: list[ApplicationSummaryOut]
    earnings: EarningsOut
    reputation: ReputationOut
    ai_reviews: list[AIReviewOut]


# ── Helpers ──────────────────────────────────────────────────────────────────


def _parse_payload(payload_json: str) -> dict:
    try:
        return json.loads(payload_json)
    except (json.JSONDecodeError, TypeError):
        return {}


def _badge_tier(score: int) -> str:
    if score >= 90:
        return "gold"
    if score >= 70:
        return "silver"
    if score >= 50:
        return "bronze"
    return "none"


# ── Client dashboard ────────────────────────────────────────────────────────


@router.get("/client", response_model=ClientDashboardResponse)
async def client_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ClientDashboardResponse:
    user_id = request.state.user_id

    # 1. Active gigs owned by the client (non-terminal statuses)
    active_statuses = (
        GigStatus.DRAFT,
        GigStatus.OPEN,
        GigStatus.IN_PROGRESS,
        GigStatus.DISPUTED,
    )
    gigs_q = (
        select(GigModel)
        .where(GigModel.client_id == user_id, GigModel.status.in_(active_statuses))
        .order_by(GigModel.created_at.desc())
    )
    gigs = (await db.execute(gigs_q)).scalars().all()
    gig_ids = [g.id for g in gigs]

    # 2. Proposal counts per gig
    proposal_counts: dict[str, int] = {}
    if gig_ids:
        pc_q = (
            select(ProposalModel.gig_id, func.count())
            .where(ProposalModel.gig_id.in_(gig_ids))
            .group_by(ProposalModel.gig_id)
        )
        for row in (await db.execute(pc_q)).all():
            proposal_counts[row[0]] = row[1]

    # 3. Escrow info per gig (using gig total_amount as balance proxy)
    escrow_gig_ids: set[str] = set()
    if gig_ids:
        esc_q = select(EscrowContractModel.gig_id).where(
            EscrowContractModel.gig_id.in_(gig_ids)
        )
        escrow_gig_ids = {r[0] for r in (await db.execute(esc_q)).all()}

    # Client user info for gig output
    client_user = (
        await db.execute(select(UserModel).where(UserModel.id == user_id))
    ).scalar_one_or_none()

    # Build active gig list
    all_gig_ids = [g.id for g in gigs]

    # Fetch milestones for active gigs
    milestones_by_gig: dict[str, list[MilestoneModel]] = {}
    if all_gig_ids:
        ms_q = (
            select(MilestoneModel)
            .where(MilestoneModel.gig_id.in_(all_gig_ids))
            .order_by(MilestoneModel.order)
        )
        for m in (await db.execute(ms_q)).scalars().all():
            milestones_by_gig.setdefault(m.gig_id, []).append(m)

    active_gigs_out: list[ActiveGigOut] = []
    escrow_per_gig: list[EscrowPerGigOut] = []
    total_locked = 0

    for g in gigs:
        has_escrow = g.id in escrow_gig_ids
        # Escrow balance = sum of non-PAID milestone amounts for gigs with escrow
        gig_milestones = milestones_by_gig.get(g.id, [])
        if has_escrow:
            locked = sum(
                int(m.amount)
                for m in gig_milestones
                if m.status != MilestoneStatus.PAID
            )
            escrow_per_gig.append(
                EscrowPerGigOut(gig_id=g.id, title=g.title, amount=str(locked))
            )
            total_locked += locked
        else:
            locked = 0

        ms_out = [
            GigMilestoneOut(
                id=m.id,
                gig_id=m.gig_id,
                title=m.title,
                description=m.description,
                amount=m.amount,
                currency=g.currency,
                status=m.status,
                order=m.order,
                due_date=m.due_date.isoformat() if m.due_date else None,
            )
            for m in gig_milestones
        ]

        active_gigs_out.append(
            ActiveGigOut(
                id=g.id,
                client_id=g.client_id,
                client_name=client_user.name if client_user else None,
                client_avatar_url=client_user.avatar_url if client_user else None,
                client_wallet_address=client_user.wallet_address
                if client_user
                else None,
                freelancer_id=g.freelancer_id,
                title=g.title,
                description=g.description,
                category=None,
                skills=g.required_skills or [],
                total_amount=g.total_amount,
                currency=g.currency,
                status=g.status,
                deadline=g.deadline.isoformat() if g.deadline else None,
                created_at=g.created_at.isoformat(),
                milestones=ms_out,
                proposal_count=proposal_counts.get(g.id, 0),
                escrow_balance=str(locked),
            )
        )

    # 4. Pending actions: milestones in SUBMITTED status (need client review)
    pending_actions: list[PendingActionOut] = []
    if gig_ids:
        sub_q = (
            select(MilestoneModel, GigModel.title.label("gig_title"))
            .join(GigModel, GigModel.id == MilestoneModel.gig_id)
            .where(
                MilestoneModel.gig_id.in_(gig_ids),
                MilestoneModel.status == MilestoneStatus.SUBMITTED,
            )
            .order_by(MilestoneModel.updated_at.desc())
        )
        for row in (await db.execute(sub_q)).all():
            ms = row[0]
            gig_title = row[1]
            pending_actions.append(
                PendingActionOut(
                    type="submission",
                    gig_id=ms.gig_id,
                    gig_title=gig_title,
                    label=f"Review submission for '{ms.title}'",
                    link=f"/gigs/{ms.gig_id}/milestones/{ms.id}",
                    created_at=ms.updated_at.isoformat(),
                )
            )

    # Also add pending proposals as actions
    if gig_ids:
        pp_q = (
            select(ProposalModel, GigModel.title.label("gig_title"))
            .join(GigModel, GigModel.id == ProposalModel.gig_id)
            .where(
                ProposalModel.gig_id.in_(gig_ids),
                ProposalModel.status == ProposalStatus.PENDING,
            )
            .order_by(ProposalModel.created_at.desc())
        )
        for row in (await db.execute(pp_q)).all():
            prop = row[0]
            gig_title = row[1]
            pending_actions.append(
                PendingActionOut(
                    type="proposal",
                    gig_id=prop.gig_id,
                    gig_title=gig_title,
                    label="New proposal received",
                    link=f"/gigs/{prop.gig_id}/proposals",
                    created_at=prop.created_at.isoformat(),
                )
            )

    # 5. Recent activity (last 20 notifications)
    notif_q = (
        select(NotificationModel)
        .where(NotificationModel.user_id == user_id)
        .order_by(NotificationModel.created_at.desc())
        .limit(20)
    )
    notifs = (await db.execute(notif_q)).scalars().all()
    recent_activity = [
        ActivityEventOut(
            id=n.id,
            type=n.type,
            message=_parse_payload(n.payload_json).get("message", n.type),
            gig_id=_parse_payload(n.payload_json).get("gig_id", ""),
            created_at=n.created_at.isoformat(),
        )
        for n in notifs
    ]

    # 6. Stats
    total_gigs_q = (
        select(func.count()).select_from(GigModel).where(GigModel.client_id == user_id)
    )
    total_gigs = (await db.execute(total_gigs_q)).scalar() or 0

    active_freelancers_q = (
        select(func.count(func.distinct(GigModel.freelancer_id)))
        .select_from(GigModel)
        .where(
            GigModel.client_id == user_id,
            GigModel.freelancer_id.isnot(None),
            GigModel.status.in_((GigStatus.IN_PROGRESS, GigStatus.DISPUTED)),
        )
    )
    active_freelancers = (await db.execute(active_freelancers_q)).scalar() or 0

    return ClientDashboardResponse(
        active_gigs=active_gigs_out,
        pending_actions=pending_actions,
        escrow_overview=EscrowOverviewOut(
            total_locked=str(total_locked),
            per_gig=escrow_per_gig,
        ),
        recent_activity=recent_activity,
        stats=ClientStatsOut(
            total_gigs=total_gigs,
            active_freelancers=active_freelancers,
            avg_approval_time="0",
        ),
    )


# ── Freelancer dashboard ────────────────────────────────────────────────────


@router.get("/freelancer", response_model=FreelancerDashboardResponse)
async def freelancer_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> FreelancerDashboardResponse:
    user_id = request.state.user_id

    # 1. Active milestones: milestones on gigs where freelancer_id = user
    active_ms_q = (
        select(MilestoneModel, GigModel.title.label("gig_title"))
        .join(GigModel, GigModel.id == MilestoneModel.gig_id)
        .where(
            GigModel.freelancer_id == user_id,
            MilestoneModel.status.in_(
                (
                    MilestoneStatus.PENDING,
                    MilestoneStatus.IN_PROGRESS,
                    MilestoneStatus.SUBMITTED,
                    MilestoneStatus.REVISION_REQUESTED,
                )
            ),
        )
        .order_by(MilestoneModel.order)
    )
    active_milestones: list[ActiveMilestoneOut] = []
    for row in (await db.execute(active_ms_q)).all():
        ms = row[0]
        gig_title = row[1]
        active_milestones.append(
            ActiveMilestoneOut(
                id=ms.id,
                gig_id=ms.gig_id,
                gig_title=gig_title,
                milestone_name=ms.title,
                budget=ms.amount,
                status=ms.status,
                deadline=ms.due_date.isoformat() if ms.due_date else None,
            )
        )

    # 2. Applications (proposals by this freelancer)
    apps_q = (
        select(ProposalModel, GigModel.title.label("gig_title"))
        .join(GigModel, GigModel.id == ProposalModel.gig_id)
        .where(ProposalModel.freelancer_id == user_id)
        .order_by(ProposalModel.created_at.desc())
    )
    applications: list[ApplicationSummaryOut] = []
    for row in (await db.execute(apps_q)).all():
        prop = row[0]
        gig_title = row[1]
        applications.append(
            ApplicationSummaryOut(
                id=prop.id,
                gig_id=prop.gig_id,
                gig_title=gig_title,
                status=prop.status,
                created_at=prop.created_at.isoformat(),
            )
        )

    # 3. Earnings: milestones with status PAID on gigs where freelancer_id = user
    paid_ms_q = (
        select(MilestoneModel)
        .join(GigModel, GigModel.id == MilestoneModel.gig_id)
        .where(
            GigModel.freelancer_id == user_id,
            MilestoneModel.status == MilestoneStatus.PAID,
        )
    )
    paid_milestones = (await db.execute(paid_ms_q)).scalars().all()

    total_earned = sum(int(m.amount) for m in paid_milestones)

    # Pending payment: APPROVED milestones not yet paid
    pending_ms_q = (
        select(func.coalesce(func.sum(func.cast(MilestoneModel.amount, Integer)), 0))
        .join(GigModel, GigModel.id == MilestoneModel.gig_id)
        .where(
            GigModel.freelancer_id == user_id,
            MilestoneModel.status == MilestoneStatus.APPROVED,
        )
    )
    pending_payment = (await db.execute(pending_ms_q)).scalar() or 0

    # Last 30 days earnings breakdown
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    last_30: list[EarningsDayOut] = []
    # Group paid milestones by date
    daily_earnings: dict[str, int] = {}
    for m in paid_milestones:
        if m.updated_at and m.updated_at >= thirty_days_ago:
            day = m.updated_at.strftime("%Y-%m-%d")
            daily_earnings[day] = daily_earnings.get(day, 0) + int(m.amount)
    for day in sorted(daily_earnings.keys()):
        last_30.append(EarningsDayOut(date=day, amount=str(daily_earnings[day])))

    # 4. Reputation: based on review reports
    reviews_q = (
        select(ReviewReportModel)
        .join(SubmissionModel, SubmissionModel.id == ReviewReportModel.submission_id)
        .where(SubmissionModel.freelancer_id == user_id)
        .order_by(ReviewReportModel.created_at.desc())
    )
    reviews = (await db.execute(reviews_q)).scalars().all()
    avg_score = round(sum(r.score for r in reviews) / len(reviews)) if reviews else 0
    recent_reviews = [
        RecentReviewOut(
            score=r.score,
            review=r.body if r.body else None,
            created_at=r.created_at.isoformat(),
        )
        for r in reviews[:5]
    ]

    # 5. AI reviews: join review_reports -> submissions -> milestones
    ai_q = (
        select(
            ReviewReportModel,
            MilestoneModel.title.label("milestone_name"),
        )
        .join(SubmissionModel, SubmissionModel.id == ReviewReportModel.submission_id)
        .join(MilestoneModel, MilestoneModel.id == SubmissionModel.milestone_id)
        .join(GigModel, GigModel.id == MilestoneModel.gig_id)
        .where(GigModel.freelancer_id == user_id)
        .order_by(ReviewReportModel.created_at.desc())
        .limit(20)
    )
    ai_reviews: list[AIReviewOut] = []
    for row in (await db.execute(ai_q)).all():
        rr = row[0]
        ms_name = row[1]
        ai_reviews.append(
            AIReviewOut(
                milestone_name=ms_name,
                verdict=rr.verdict,
                score=rr.score,
                created_at=rr.created_at.isoformat(),
            )
        )

    return FreelancerDashboardResponse(
        active_milestones=active_milestones,
        applications=applications,
        earnings=EarningsOut(
            total_earned=str(total_earned),
            pending_payment=str(pending_payment),
            last_30_days=last_30,
        ),
        reputation=ReputationOut(
            score=avg_score,
            badge_tier=_badge_tier(avg_score),
            recent_reviews=recent_reviews,
        ),
        ai_reviews=ai_reviews,
    )
