// Proto-derived enum constants for the web layer.
//
// Source of truth: packages/schema/proto/api/v1/*.proto
// Generated reference: packages/schema/generated/ts/api/v1/*_pb.ts
//
// These mirror the proto enum values so that the web layer can reference
// canonical constants without importing the full protobuf runtime.
// If a proto enum changes, update this file to match.

// ── api/v1/user.proto ────────────────────────────────────────────────────────

export enum UserRole {
  UNSPECIFIED = 0,
  FREELANCER = 1,
  CLIENT = 2,
  ADMIN = 3,
}

export enum UserStatus {
  UNSPECIFIED = 0,
  ACTIVE = 1,
  SUSPENDED = 2,
}

// ── api/v1/gig.proto ─────────────────────────────────────────────────────────

export enum GigStatus {
  UNSPECIFIED = 0,
  DRAFT = 1,
  OPEN = 2,
  IN_PROGRESS = 3,
  COMPLETED = 4,
  CANCELLED = 5,
  DISPUTED = 6,
}

export enum Currency {
  UNSPECIFIED = 0,
  ETH = 1,
  USDC = 2,
}

// ── api/v1/milestone.proto ───────────────────────────────────────────────────

export enum MilestoneStatus {
  UNSPECIFIED = 0,
  PENDING = 1,
  SUBMITTED = 2,
  UNDER_REVIEW = 3,
  APPROVED = 4,
  REVISION_REQUESTED = 5,
  PAID = 6,
  DISPUTED = 7,
}

// ── api/v1/submission.proto ──────────────────────────────────────────────────

export enum SubmissionStatus {
  UNSPECIFIED = 0,
  PENDING = 1,
  UNDER_REVIEW = 2,
  APPROVED = 3,
  REJECTED = 4,
}

// ── api/v1/proposal.proto ────────────────────────────────────────────────────

export enum ProposalStatus {
  UNSPECIFIED = 0,
  PENDING = 1,
  ACCEPTED = 2,
  REJECTED = 3,
  WITHDRAWN = 4,
}

// ── api/v1/dispute.proto ─────────────────────────────────────────────────────

export enum DisputeStatus {
  UNSPECIFIED = 0,
  OPEN = 1,
  // 2 reserved (was DISCUSSION; lifecycle is OPEN -> ARBITRATION -> RESOLVED)
  ARBITRATION = 3,
  RESOLVED = 4,
}

export enum DisputeResolution {
  UNSPECIFIED = 0,
  PAY_FREELANCER = 1,
  REFUND_CLIENT = 2,
  SPLIT = 3,
}

// ── api/v1/notification.proto ────────────────────────────────────────────────

export enum NotificationType {
  UNSPECIFIED = 0,
  GIG_FUNDED = 1,
  GIG_CANCELLED = 2,
  GIG_COMPLETED = 3,
  PROPOSAL_RECEIVED = 4,
  PROPOSAL_ACCEPTED = 5,
  PROPOSAL_REJECTED = 6,
  SUBMISSION_RECEIVED = 7,
  REVISION_REQUESTED = 8,
  MILESTONE_APPROVED = 9,
  FUNDS_RELEASED = 10,
  REVIEW_COMPLETE = 11,
  DISPUTE_RAISED = 12,
  DISPUTE_RESOLVED = 13,
  REVIEW_RECEIVED = 14,
}

// ── contracts/v1/escrow.proto ────────────────────────────────────────────────

export enum EscrowStatus {
  UNSPECIFIED = 0,
  DEPLOYING = 1,
  FUNDED = 2,
  PARTIALLY_RELEASED = 3,
  SETTLED = 4,
  DISPUTED = 5,
  REFUNDED = 6,
}
