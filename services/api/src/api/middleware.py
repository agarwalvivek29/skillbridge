"""
middleware.py — Auth middleware (first in chain).

Accepts:
  - Authorization: Bearer <jwt>  → user token
  - X-API-Key: <key>             → service-to-service

Exempt paths: GET /health, GET /metrics, /v1/auth/*
"""

import logging
import re

from fastapi import Request, Response
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from src.config import settings
from src.domain.auth import decode_access_token

logger = logging.getLogger(__name__)

# Paths that bypass auth entirely (all methods)
_EXEMPT_PREFIXES = (
    "/health",
    "/metrics",
    "/v1/auth/",
    "/v1/webhooks/",  # HMAC-verified — not JWT; any future /v1/webhooks/* is also exempt
    "/docs",
    "/redoc",
    "/openapi.json",
)

# Only these GET paths are genuinely public (no auth required):
#   GET /v1/gigs                  — discovery board listing
#   GET /v1/gigs/<uuid>           — single gig detail
#   GET /v1/portfolio             — portfolio listing
#   GET /v1/portfolio/<uuid>      — single portfolio item
# Any sub-resource (e.g. /v1/gigs/<uuid>/proposals) still requires auth.
_UUID_SEGMENT = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_PUBLIC_GET_RE = re.compile(rf"^/v1/(gigs|portfolio)(/{_UUID_SEGMENT})?$")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Exempt paths (all methods)
        for prefix in _EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Exempt only the exact public GET endpoints (list + detail)
        method = request.method.upper()
        if method == "GET" and _PUBLIC_GET_RE.match(path):
            return await call_next(request)

        # --- API Key auth ---
        api_key = request.headers.get("X-API-Key")
        if api_key:
            if api_key == settings.api_key:
                logger.info("auth method=api_key subject=service")
                return await call_next(request)
            return _unauthorized("INVALID_API_KEY", "Invalid API key")

        # --- JWT Bearer auth ---
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _unauthorized("MISSING_TOKEN", "Authorization header required")

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            claims = decode_access_token(token)
            user_id = claims.get("sub", "unknown")
            logger.info("auth method=jwt subject=%s", user_id)
            # Attach claims to request state for use in handlers
            request.state.user_id = user_id
            request.state.role = claims.get("role", "")
        except JWTError:
            return _unauthorized("INVALID_TOKEN", "Token is invalid or expired")

        return await call_next(request)


def _unauthorized(code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"code": code, "message": message, "field_errors": []},
    )
