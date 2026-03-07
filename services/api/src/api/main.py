"""FastAPI application entry point for the api service."""

import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.portfolio import router as portfolio_router
from src.config import settings

# Configure structured logging
logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>"
    ),
    serialize=(settings.environment == "production"),
)

app = FastAPI(
    title="SkillBridge API",
    version="1.0.0",
    description="Core backend API for SkillBridge — AI-powered freelance platform",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Exempt endpoints (no auth required) ──────────────────────────────────────


@app.get("/health", include_in_schema=False)
async def health() -> dict:  # type: ignore[type-arg]
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> dict:  # type: ignore[type-arg]
    return {"status": "ok"}


# ─── Protected routes ─────────────────────────────────────────────────────────

app.include_router(portfolio_router)
