"""
domain/enums.py — Python StrEnum constants for status/role/currency values.

These mirror the proto enum definitions in packages/schema/proto/api/v1/.
StrEnum values serialize as plain strings, so JSON responses are unchanged.
"""

from enum import StrEnum


class UserRole(StrEnum):
    UNSPECIFIED = "USER_ROLE_UNSPECIFIED"
    FREELANCER = "USER_ROLE_FREELANCER"
    CLIENT = "USER_ROLE_CLIENT"
    ADMIN = "USER_ROLE_ADMIN"


class UserStatus(StrEnum):
    UNSPECIFIED = "USER_STATUS_UNSPECIFIED"
    ACTIVE = "USER_STATUS_ACTIVE"
    SUSPENDED = "USER_STATUS_SUSPENDED"


class GigStatus(StrEnum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"


class MilestoneStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    DISPUTED = "DISPUTED"
    RESOLVED = "RESOLVED"
    PAID = "PAID"
    REVISION_REQUESTED = "REVISION_REQUESTED"


class Currency(StrEnum):
    SOL = "SOL"
    USDC = "USDC"


class ProposalStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class SubmissionStatus(StrEnum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class EscrowStatus(StrEnum):
    DEPLOYING = "ESCROW_STATUS_DEPLOYING"
    FUNDED = "ESCROW_STATUS_FUNDED"
    PARTIALLY_RELEASED = "ESCROW_STATUS_PARTIALLY_RELEASED"
    SETTLED = "ESCROW_STATUS_SETTLED"
    DISPUTED = "ESCROW_STATUS_DISPUTED"
    REFUNDED = "ESCROW_STATUS_REFUNDED"


class ReviewVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
