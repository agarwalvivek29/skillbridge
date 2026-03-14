/**
 * @proto packages/schema/proto/api/v1/dispute.proto — Dispute
 *
 * The proto Dispute.reason is a free-text string field. The frontend defines
 * a constrained union type for UI rendering. These values are frontend-defined
 * categories, not proto enum values.
 */
export type DisputeReason =
  | "WORK_DOESNT_MEET_REQUIREMENTS"
  | "CLIENT_UNRESPONSIVE"
  | "SCOPE_CREEP"
  | "PAYMENT_WITHHELD"
  | "OTHER";

/**
 * @proto packages/schema/proto/api/v1/dispute.proto — DisputeStatus enum
 *
 * Maps proto DisputeStatus enum values (DISPUTE_STATUS_OPEN, etc.) to
 * short string union values used in the frontend.
 */
export type DisputeStatus = "OPEN" | "DISCUSSION" | "ARBITRATION" | "RESOLVED";

/**
 * @proto packages/schema/proto/api/v1/dispute.proto — DisputeResolution enum
 *
 * Simplified frontend mapping:
 *   "client"     ← proto DISPUTE_RESOLUTION_REFUND_CLIENT
 *   "freelancer" ← proto DISPUTE_RESOLUTION_PAY_FREELANCER
 *
 * Proto value NOT mapped:
 *   DISPUTE_RESOLUTION_SPLIT (handled differently in resolution details)
 */
export type DisputeVerdict = "client" | "freelancer";

/**
 * @proto packages/schema/proto/api/v1/dispute.proto — DisputeMessage
 *
 * Field mappings:
 *   id         = proto DisputeMessage.id
 *   dispute_id = proto DisputeMessage.dispute_id
 *   author_id  ← proto DisputeMessage.user_id
 *   body       ← proto DisputeMessage.content
 *   created_at = proto DisputeMessage.created_at (Timestamp → ISO string)
 *
 * Frontend-only / API-enriched fields:
 *   author_name — API-enriched (joined from User.name)
 *   author_role — API-enriched (derived from gig participant roles)
 *   file_keys   — API-enriched (not in proto DisputeMessage)
 */
export interface DisputeEvidence {
  id: string;
  dispute_id: string;
  author_id: string;
  author_name: string;
  author_role: "client" | "freelancer" | "arbitrator";
  body: string;
  file_keys: string[];
  created_at: string;
}

/**
 * Frontend-only type — no direct proto equivalent.
 * Represents status transition events constructed from Dispute state changes.
 */
export interface DisputeTimelineEvent {
  id: string;
  status: DisputeStatus;
  note: string;
  created_at: string;
}

/**
 * Frontend-only type — no direct proto equivalent.
 * Represents a community arbitrator assigned to a dispute.
 */
export interface Arbitrator {
  id: string;
  name: string;
  avatar_url: string | null;
}

/**
 * @proto packages/schema/proto/api/v1/dispute.proto — Dispute (resolution fields)
 *
 * Field mappings:
 *   winner          ← proto Dispute.resolution (enum → "client" | "freelancer")
 *   amount_released ← proto Dispute.freelancer_split_amount
 *   resolved_at     = proto Dispute.resolved_at (Timestamp → ISO string)
 *
 * Frontend-only / API-enriched fields:
 *   reasoning       — API-enriched (not in proto)
 *   amount_refunded — API-enriched (computed as total - amount_released)
 */
export interface DisputeResolution {
  winner: DisputeVerdict;
  reasoning: string;
  amount_released: string;
  amount_refunded: string;
  resolved_at: string;
}

/**
 * @proto packages/schema/proto/api/v1/dispute.proto — Dispute
 *
 * Field mappings:
 *   id             = proto Dispute.id
 *   milestone_id   = proto Dispute.milestone_id
 *   gig_id         = proto Dispute.gig_id
 *   filed_by       ← proto Dispute.raised_by_user_id
 *   reason         = proto Dispute.reason
 *   description    — API-enriched (expanded from proto reason)
 *   status         = proto Dispute.status (enum DisputeStatus → string union)
 *   ai_review_summary ← proto Dispute.ai_evidence_summary
 *   created_at     = proto Dispute.created_at (Timestamp → ISO string)
 *   updated_at     = proto Dispute.updated_at (Timestamp → ISO string)
 *
 * Frontend-only / API-enriched fields:
 *   milestone_title        — API-enriched (joined from Milestone.title)
 *   gig_title              — API-enriched (joined from Gig.title)
 *   filed_by_name          — API-enriched (joined from User.name)
 *   filed_by_role          — API-enriched (derived from gig participant roles)
 *   include_ai_review      — API-enriched (not in proto)
 *   client_id              — API-enriched (from Gig)
 *   client_name            — API-enriched (joined from User.name)
 *   client_avatar_url      — API-enriched (joined from User.avatar_url)
 *   freelancer_id          — API-enriched (from Gig)
 *   freelancer_name        — API-enriched (joined from User.name)
 *   freelancer_avatar_url  — API-enriched (joined from User.avatar_url)
 *   evidence               — API-enriched (DisputeEvidence[])
 *   timeline               — API-enriched (DisputeTimelineEvent[])
 *   arbitrators            — API-enriched (Arbitrator[])
 *   resolution             — API-enriched (DisputeResolution | null)
 *   ai_review_verdict      — API-enriched (from ai-reviewer)
 *   ai_review_score        — API-enriched (from ai-reviewer)
 *
 * Proto fields NOT mapped:
 *   Dispute.freelancer_split_amount, Dispute.resolution_tx_hash,
 *   Dispute.discussion_deadline
 */
export interface Dispute {
  id: string;
  milestone_id: string;
  milestone_title: string;
  gig_id: string;
  gig_title: string;
  filed_by: string;
  filed_by_name: string;
  filed_by_role: "client" | "freelancer";
  reason: DisputeReason;
  description: string;
  include_ai_review: boolean;
  status: DisputeStatus;
  client_id: string;
  client_name: string;
  client_avatar_url: string | null;
  freelancer_id: string;
  freelancer_name: string;
  freelancer_avatar_url: string | null;
  evidence: DisputeEvidence[];
  timeline: DisputeTimelineEvent[];
  arbitrators: Arbitrator[];
  resolution: DisputeResolution | null;
  ai_review_summary: string | null;
  ai_review_verdict: "PASS" | "FAIL" | null;
  ai_review_score: number | null;
  created_at: string;
  updated_at: string;
}

/**
 * Frontend-only composite type — no direct proto equivalent.
 * Aggregated view of a dispute for the arbitrator dashboard.
 * Fields derived from Dispute, Gig, Milestone, and User proto messages.
 */
export interface ArbitrationCase {
  id: string;
  dispute_id: string;
  gig_title: string;
  milestone_title: string;
  filed_date: string;
  deadline: string;
  status: DisputeStatus;
  client_name: string;
  freelancer_name: string;
}

/**
 * Frontend-only type — no direct proto equivalent.
 * Represents an arbitrator's vote on a dispute.
 */
export interface ArbitrationVote {
  arbitrator_id: string;
  arbitrator_name: string;
  verdict: DisputeVerdict;
  reasoning: string;
  voted_at: string;
}

/**
 * @proto packages/schema/proto/api/v1/dispute.proto — RaiseDisputeRequest
 *
 * Field mappings:
 *   milestone_id = proto RaiseDisputeRequest.milestone_id
 *   reason       = proto RaiseDisputeRequest.reason
 *
 * Frontend-only fields:
 *   description, evidence_file_keys, include_ai_review — not in proto request
 */
export interface CreateDisputePayload {
  milestone_id: string;
  reason: DisputeReason;
  description: string;
  evidence_file_keys: string[];
  include_ai_review: boolean;
}

/**
 * @proto packages/schema/proto/api/v1/dispute.proto — PostDisputeMessageRequest
 *
 * Field mappings:
 *   body ← proto PostDisputeMessageRequest.content
 *
 * Frontend-only fields:
 *   file_keys — not in proto request
 */
export interface SubmitEvidencePayload {
  body: string;
  file_keys: string[];
}

/**
 * Frontend-only type — no direct proto equivalent.
 * Payload for arbitrator vote submission.
 */
export interface CastVotePayload {
  verdict: DisputeVerdict;
  reasoning: string;
}
