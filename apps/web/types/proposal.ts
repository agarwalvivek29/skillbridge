/**
 * @proto packages/schema/proto/api/v1/proposal.proto — Proposal
 *
 * Field mappings:
 *   id             = proto Proposal.id
 *   gig_id         = proto Proposal.gig_id
 *   freelancer_id  = proto Proposal.freelancer_id
 *   cover_letter   = proto Proposal.cover_letter
 *   status         = proto Proposal.status (enum ProposalStatus → string)
 *   created_at     = proto Proposal.created_at (Timestamp → ISO string)
 *
 * Frontend-only / API-enriched fields:
 *   freelancer_name             — API-enriched (joined from User.name)
 *   freelancer_avatar_url       — API-enriched (joined from User.avatar_url)
 *   freelancer_wallet_address   — API-enriched (joined from User.wallet_address)
 *   freelancer_rating           — API-enriched (from Reputation/Review data)
 *   freelancer_reputation_score — API-enriched (from Reputation data)
 *   proposed_rate               — API-enriched (not in proto; proto has estimated_days)
 *   timeline                    — API-enriched (MilestoneTimeline[], not in proto)
 *   attachments                 — API-enriched (not in proto)
 *   reject_message              — API-enriched (not in proto)
 *
 * Proto fields NOT mapped:
 *   Proposal.estimated_days, Proposal.updated_at
 */
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

/**
 * Frontend-only type — no direct proto equivalent.
 * Used to map proposed delivery dates to individual milestones in a proposal.
 */
export interface MilestoneTimeline {
  milestone_id: string;
  estimated_delivery: string;
}

/**
 * @proto packages/schema/proto/api/v1/proposal.proto — GetProposalsResponse
 *
 * Maps to proto GetProposalsResponse. Pagination flattened from PaginationMeta.
 *
 * Frontend-only / API-enriched fields:
 *   total — API-enriched (from PaginationMeta.total_count)
 */
export interface ProposalListResponse {
  proposals: Proposal[];
  total: number;
}
