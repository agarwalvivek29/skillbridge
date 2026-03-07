"""
FastAPI application factory.

Middleware and route registration order:
  1. /health  (no auth)  — registered BEFORE auth middleware
  2. /metrics (no auth)  — registered BEFORE auth middleware
  3. Auth dependency     — applied via router dependency on all /v1/* routes
  4. All /v1/* routes
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from prometheus_fastapi_instrumentator import Instrumentator

from api.api.auth import router as auth_router
from api.api.health import router as health_router
from api.config import settings
from api.domain.auth import verify_jwt

log = structlog.get_logger()

# ─── Auth dependency (shared by all protected routers) ────────────────────────

_bearer = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_auth(
    api_key: str | None = Security(_api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> dict:
    """FastAPI dependency — validates API key or JWT Bearer token."""
    if api_key and api_key == settings.api_key:
        log.info("auth.success", method="api-key", subject="service")
        return {"subject": "service", "method": "api-key"}

    if credentials:
        try:
            payload = verify_jwt(credentials.credentials, settings.jwt_secret)
            subject = payload.get("sub", "")
            log.info("auth.success", method="jwt", subject=f"user:{subject}")
            return {
                "subject": subject,
                "method": "jwt",
                "role": payload.get("role"),
            }
        except JWTError:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "UNAUTHORIZED", "message": "Valid API key or Bearer token required"},
    )


# ─── App factory ─────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("api.startup", port=settings.port)
    yield
    log.info("api.shutdown")


app = FastAPI(
    title="SkillBridge API",
    version="0.1.0",
    lifespan=lifespan,
)

# Prometheus /metrics — registered BEFORE auth; no auth dependency
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Health check — registered BEFORE auth; no auth dependency
app.include_router(health_router)

# Auth routes — no auth dependency (they produce tokens)
app.include_router(auth_router)

# All future /v1/* routers should include: dependencies=[Depends(require_auth)]
# Example:
#   from api.api.gigs import router as gigs_router
#   app.include_router(gigs_router, dependencies=[Depends(require_auth)])
