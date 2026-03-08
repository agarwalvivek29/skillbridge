export type DisputeReason =
  | "WORK_DOESNT_MEET_REQUIREMENTS"
  | "CLIENT_UNRESPONSIVE"
  | "SCOPE_CREEP"
  | "PAYMENT_WITHHELD"
  | "OTHER";

export type DisputeStatus = "OPEN" | "DISCUSSION" | "ARBITRATION" | "RESOLVED";

export type DisputeVerdict = "client" | "freelancer";

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

export interface DisputeTimelineEvent {
  id: string;
  status: DisputeStatus;
  note: string;
  created_at: string;
}

export interface Arbitrator {
  id: string;
  name: string;
  avatar_url: string | null;
}

export interface DisputeResolution {
  winner: DisputeVerdict;
  reasoning: string;
  amount_released: string;
  amount_refunded: string;
  resolved_at: string;
}

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

export interface ArbitrationVote {
  arbitrator_id: string;
  arbitrator_name: string;
  verdict: DisputeVerdict;
  reasoning: string;
  voted_at: string;
}

export interface CreateDisputePayload {
  milestone_id: string;
  reason: DisputeReason;
  description: string;
  evidence_file_keys: string[];
  include_ai_review: boolean;
}

export interface SubmitEvidencePayload {
  body: string;
  file_keys: string[];
}

export interface CastVotePayload {
  verdict: DisputeVerdict;
  reasoning: string;
}
