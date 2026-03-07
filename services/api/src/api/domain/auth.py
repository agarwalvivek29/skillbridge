"""
Auth domain logic — password hashing and JWT operations.

Zero framework imports. All functions are pure and independently testable.
"""

from datetime import UTC, datetime

import bcrypt
from jose import jwt

_BCRYPT_ROUNDS = 12


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt (cost 12). Returns the hash string."""
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if the plaintext password matches the bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def issue_jwt(
    subject: str,
    secret: str,
    expiry_seconds: int,
    role: str = "USER_ROLE_MEMBER",
) -> str:
    """
    Sign and return a JWT with the given subject and role.

    Claims:
      sub   — user ID (UUID string)
      role  — UserRole enum name
      iat   — issued-at (UTC epoch seconds)
      exp   — expiry (UTC epoch seconds)
    """
    now = int(datetime.now(UTC).timestamp())
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + expiry_seconds,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_jwt(token: str, secret: str) -> dict:
    """
    Verify the JWT signature and expiry. Returns the decoded payload dict.

    Raises jose.JWTError if the token is invalid or expired.
    """
    return jwt.decode(token, secret, algorithms=["HS256"])


__all__ = ["hash_password", "verify_password", "issue_jwt", "verify_jwt"]
