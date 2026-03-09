"""main.py — FastAPI application entry point."""

import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from src.config import settings
from src.api.auth import router as auth_router
from src.api.webhooks import router as webhooks_router
from src.api.gig import router as gig_router
from src.api.middleware import AuthMiddleware
from src.api.portfolio import router as portfolio_router
from src.api.proposal import router as proposal_router
from src.api.milestone import router as milestone_approval_router
from src.api.reputation import router as reputation_router
from src.api.submission import milestone_router as submission_milestone_router
from src.api.submission import submission_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(
    title="SkillBridge API", version="0.1.0", docs_url="/docs", redoc_url="/redoc"
)


@app.on_event("startup")
async def _startup_checks() -> None:
    if not settings.github_webhook_secret:
        logger.warning("GITHUB_WEBHOOK_SECRET is not set")


app.add_middleware(AuthMiddleware)
app.include_router(auth_router)
app.include_router(gig_router)
app.include_router(portfolio_router)
app.include_router(proposal_router)
app.include_router(submission_milestone_router)
app.include_router(submission_router)
app.include_router(milestone_approval_router)
app.include_router(reputation_router)
app.include_router(webhooks_router)


@app.get("/health", tags=["infra"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics", tags=["infra"])
async def metrics() -> dict:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def _unhandled(request, exc):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "field_errors": [],
        },
    )
