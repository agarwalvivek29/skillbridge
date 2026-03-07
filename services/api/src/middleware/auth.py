"""Auth middleware — FastAPI dependency for JWT and API key authentication.

Every route must depend on `require_auth`. Only /health and /metrics are exempt.
"""

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from src.config import settings

_bearer = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_auth(
    api_key: str | None = Security(_api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> dict:  # type: ignore[type-arg]
    """FastAPI dependency — inject into any router that needs protection."""
    if api_key and api_key == settings.api_key:
        return {"subject": "service", "method": "api-key"}

    if credentials:
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret,
                algorithms=["HS256"],
            )
            return {
                "subject": payload.get("sub", ""),
                "method": "jwt",
                "role": payload.get("role"),
                "scopes": payload.get("scopes", []),
            }
        except jwt.InvalidTokenError:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "UNAUTHORIZED",
            "message": "Valid API key or Bearer token required",
            "field_errors": [],
        },
    )
