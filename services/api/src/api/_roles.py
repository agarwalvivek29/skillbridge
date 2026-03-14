"""
_roles.py — Shared role-string constants for auth checks.

These values match the role strings stored in JWT claims and the UserModel.role column.
Import from here rather than hardcoding strings in individual routers.
"""

from src.domain.enums import UserRole

ROLE_FREELANCER = UserRole.FREELANCER
ROLE_CLIENT = UserRole.CLIENT
ROLE_ADMIN = UserRole.ADMIN
