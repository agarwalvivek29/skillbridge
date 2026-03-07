"""
main.py — FastAPI application entry point.

Middleware order (LIFO for requests):
  1. AuthMiddleware     ← first to run on inbound (innermost in Starlette chain)
  2. (future: logging, rate-limit, etc.)

Add auth middleware LAST in the `add_middleware` chain so it executes FIRST.
"""

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.api.auth import router as auth_router
from src.api.gig import router as gig_router
from src.api.middleware import AuthMiddleware
from src.api.portfolio import router as portfolio_router
from src.api.proposal import router as proposal_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SkillBridge API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware (add_middleware inserts at front of stack — last added = first executed) ──
app.add_middleware(AuthMiddleware)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(gig_router)
app.include_router(portfolio_router)
app.include_router(proposal_router)


# ── Infrastructure routes (exempt from auth) ──────────────────────────────────
@app.get("/health", tags=["infra"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics", tags=["infra"])
async def metrics() -> dict:
    # Stub — replace with Prometheus exposition format when needed
    return {"status": "ok"}


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def _unhandled(request, exc):  # noqa: ANN001
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "field_errors": [],
        },
    )
