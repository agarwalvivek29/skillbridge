/**
 * @proto packages/schema/proto/api/v1/milestone.proto — Milestone
 *
 * Field mappings:
 *   id          = proto Milestone.id
 *   gig_id      = proto Milestone.gig_id
 *   title       = proto Milestone.title
 *   description = proto Milestone.description
 *   amount      = proto Milestone.amount
 *   status      = proto Milestone.status (enum MilestoneStatus → string)
 *   order       = proto Milestone.order
 *   due_date    = proto Milestone.due_date (Timestamp → ISO string | null)
 *
 * Frontend-only / API-enriched fields:
 *   currency    — API-enriched (derived from parent Gig.currency, not on proto Milestone)
 *
 * Proto fields NOT mapped:
 *   Milestone.acceptance_criteria, Milestone.contract_index,
 *   Milestone.revision_count, Milestone.created_at, Milestone.updated_at
 */
export interface Milestone {
  id: string;
  gig_id: string;
  title: string;
  description: string;
  amount: string;
  currency: string;
  status: string;
  order: number;
  due_date: string | null;
}

/**
 * @proto packages/schema/proto/api/v1/gig.proto — Gig
 *
 * Field mappings:
 *   id              = proto Gig.id
 *   client_id       = proto Gig.client_id
 *   freelancer_id   = proto Gig.freelancer_id
 *   title           = proto Gig.title
 *   description     = proto Gig.description
 *   required_skills = proto Gig.required_skills
 *   tags            = proto Gig.tags
 *   total_amount    = proto Gig.total_amount
 *   currency        = proto Gig.currency (enum Currency → string)
 *   status          = proto Gig.status (enum GigStatus → string)
 *   deadline        = proto Gig.deadline (Timestamp → ISO string | null)
 *   created_at      = proto Gig.created_at (Timestamp → ISO string)
 *   milestones      — nested from api/v1/milestone.proto Milestone[]
 *
 * Frontend-only / API-enriched fields:
 *   client_name            — API-enriched (joined from User.name)
 *   client_avatar_url      — API-enriched (joined from User.avatar_url)
 *   client_wallet_address  — API-enriched (joined from User.wallet_address)
 *   skills                 — API-enriched (duplicate/alias of required_skills)
 *   category               — API-enriched (not in proto)
 *
 * Proto fields NOT mapped:
 *   Gig.token_address, Gig.contract_address, Gig.updated_at
 */
export interface Gig {
  id: string;
  client_id: string;
  client_name: string | null;
  client_avatar_url: string | null;
  client_wallet_address: string | null;
  freelancer_id: string | null;
  title: string;
  description: string;
  category: string | null;
  skills: string[];
  required_skills: string[];
  tags: string[];
  total_amount: string;
  currency: string;
  status: string;
  deadline: string | null;
  created_at: string;
  milestones: Milestone[];
}

/**
 * @proto packages/schema/proto/api/v1/gig.proto — GetGigsResponse
 *
 * Maps to proto GetGigsResponse with pagination from common/v1/pagination.proto.
 *
 * Frontend-only / API-enriched fields:
 *   page, page_size, total_pages — API-enriched (flattened from PaginationMeta)
 */
export interface GigListResponse {
  gigs: Gig[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
