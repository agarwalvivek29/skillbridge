"""
_roles.py — Shared role-string constants for auth checks.

These values match the role strings stored in JWT claims and the UserModel.role column.
Import from here rather than hardcoding strings in individual routers.
"""

ROLE_FREELANCER = "USER_ROLE_FREELANCER"
ROLE_CLIENT = "USER_ROLE_CLIENT"
ROLE_ADMIN = "USER_ROLE_ADMIN"
