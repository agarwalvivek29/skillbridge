// View model for API JSON responses. Proto source: packages/schema/proto/api/v1/proposal.proto
// Enums re-exported from @/types/proto; enriched fields are web-layer only.

export { ProposalStatus } from "./proto";

export interface Proposal {
  id: string;
  gig_id: string;
  freelancer_id: string;
  freelancer_name: string | null;
  freelancer_avatar_url: string | null;
  freelancer_wallet_address: string | null;
  freelancer_rating: number | null;
  freelancer_reputation_score: number | null;
  cover_letter: string;
  proposed_rate: string | null;
  timeline: MilestoneTimeline[];
  attachments: string[];
  status: string;
  reject_message: string | null;
  created_at: string;
}

export interface MilestoneTimeline {
  milestone_id: string;
  estimated_delivery: string;
}

export interface ProposalListResponse {
  proposals: Proposal[];
  total: number;
}
