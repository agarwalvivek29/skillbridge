"""middleware.py — Auth middleware (first in chain)."""

import logging
import re
from fastapi import Request, Response
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
from src.config import settings
from src.domain.auth import decode_access_token

logger = logging.getLogger(__name__)
_EXEMPT_PREFIXES = (
    "/health",
    "/metrics",
    "/v1/auth/",
    "/v1/webhooks/",
    "/v1/notifications/stream",
    "/docs",
    "/redoc",
    "/openapi.json",
)
_UUID_SEGMENT = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_WALLET_SEGMENT = r"0x[0-9a-fA-F]{40}"
_PUBLIC_GET_RE = re.compile(rf"^/v1/(gigs|portfolio)(/{_UUID_SEGMENT})?$")
_PUBLIC_REPUTATION_RE = re.compile(rf"^/v1/reputation/{_WALLET_SEGMENT}$")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        for prefix in _EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)
        method = request.method.upper()
        if method == "GET" and (
            _PUBLIC_GET_RE.match(path) or _PUBLIC_REPUTATION_RE.match(path)
        ):
            return await call_next(request)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            if api_key == settings.api_key:
                logger.info("auth method=api_key subject=service")
                return await call_next(request)
            return _unauthorized("INVALID_API_KEY", "Invalid API key")
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _unauthorized("MISSING_TOKEN", "Authorization header required")
        token = auth_header.removeprefix("Bearer ").strip()
        try:
            claims = decode_access_token(token)
            request.state.user_id = claims.get("sub", "unknown")
            request.state.role = claims.get("role", "")
        except JWTError:
            return _unauthorized("INVALID_TOKEN", "Token is invalid or expired")
        return await call_next(request)


def _unauthorized(code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401, content={"code": code, "message": message, "field_errors": []}
    )
