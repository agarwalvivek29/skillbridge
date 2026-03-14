/**
 * @proto Composite — no single proto source
 *
 * This file aggregates data from multiple proto messages for the public
 * profile view. Source protos:
 *   - packages/schema/proto/api/v1/user.proto (User, UserPublic)
 *   - packages/schema/proto/api/v1/reputation.proto (Reputation)
 *   - packages/schema/proto/api/v1/portfolio.proto (PortfolioItem)
 *   - packages/schema/proto/api/v1/review.proto (Review)
 *   - packages/schema/proto/api/v1/gig.proto (Gig)
 */
import type { PortfolioItem } from "./portfolio";

/**
 * Frontend-only type — no direct proto equivalent.
 * Represents on-chain reputation badges; data sourced from the
 * Solana reputation contract, not from proto definitions.
 */
export interface OnChainBadge {
  id: string;
  name: string;
  description: string;
  image_url: string | null;
  earned_at: string;
  tx_hash: string;
}

/**
 * @proto packages/schema/proto/api/v1/review.proto — Review
 *
 * Field mappings:
 *   id          = proto Review.id
 *   gig_id      = proto Review.gig_id
 *   reviewer_id = proto Review.reviewer_id
 *   score       ← proto Review.rating
 *   review      ← proto Review.comment
 *   created_at  = proto Review.created_at (Timestamp → ISO string)
 *
 * Frontend-only / API-enriched fields:
 *   reviewer_name   — API-enriched (joined from User.name)
 *   reviewer_avatar — API-enriched (joined from User.avatar_url)
 *   tags            — API-enriched (not in proto Review)
 *
 * Proto fields NOT mapped:
 *   Review.reviewee_id, Review.is_visible
 */
export interface Review {
  id: string;
  gig_id: string;
  reviewer_id: string;
  reviewer_name: string | null;
  reviewer_avatar: string | null;
  score: number;
  review: string | null;
  tags: string[];
  created_at: string;
}

/**
 * Composite type — aggregates from multiple proto sources.
 *
 * From user.proto UserPublic:
 *   id, wallet_address, name, bio, avatar_url, role, skills
 *
 * From reputation.proto Reputation:
 *   reputation_score  ← proto Reputation.average_ai_score (or composite)
 *   gigs_completed    = proto Reputation.gigs_completed
 *   total_earned      = proto Reputation.total_earned
 *   avg_rating        ← proto Reputation.average_rating_x100 (divided by 100)
 *   dispute_rate      ← proto Reputation.dispute_rate_pct
 *
 * Frontend-only / API-enriched fields:
 *   badge_tier       — API-enriched (computed from reputation_score thresholds)
 *   total_spent      — API-enriched (client-specific, not in proto)
 *   on_chain_badges  — API-enriched (from Solana reputation contract)
 *   portfolio_items  — API-enriched (nested PortfolioItem[])
 *   reviews          — API-enriched (nested Review[])
 *   active_gigs      — API-enriched (subset of Gig fields for active gigs)
 *   member_since     ← proto UserPublic.created_at (Timestamp → ISO string)
 */
export interface PublicProfile {
  id: string;
  wallet_address: string;
  name: string | null;
  bio: string | null;
  avatar_url: string | null;
  role: "CLIENT" | "FREELANCER";
  skills: string[];
  reputation_score: number;
  badge_tier: "BRONZE" | "SILVER" | "GOLD" | "PLATINUM";
  gigs_completed: number;
  total_earned: string | null;
  total_spent: string | null;
  avg_rating: number | null;
  dispute_rate: number | null;
  on_chain_badges: OnChainBadge[];
  portfolio_items: PortfolioItem[];
  reviews: Review[];
  active_gigs: { id: string; title: string; status: string; budget: string }[];
  member_since: string;
}
