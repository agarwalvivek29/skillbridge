import type { PortfolioItem } from "./portfolio";

export interface OnChainBadge {
  id: string;
  name: string;
  description: string;
  image_url: string | null;
  earned_at: string;
  tx_hash: string;
}

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

export interface PublicProfile {
  id: string;
  wallet_address: string;
  display_name: string | null;
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
