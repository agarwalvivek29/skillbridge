import { apiGet } from "./client";
import type { Gig } from "@/types/gig";

export interface ClientDashboard {
  active_gigs: (Gig & { proposal_count: number; escrow_balance: string })[];
  pending_actions: PendingAction[];
  escrow_overview: {
    total_locked: string;
    per_gig: { gig_id: string; title: string; amount: string }[];
  };
  recent_activity: ActivityEvent[];
  stats: {
    total_gigs: number;
    active_freelancers: number;
    avg_approval_time: string;
  };
}

export interface FreelancerDashboard {
  active_milestones: ActiveMilestone[];
  applications: ApplicationSummary[];
  earnings: {
    total_earned: string;
    pending_payment: string;
    last_30_days: { date: string; amount: string }[];
  };
  reputation: {
    score: number;
    badge_tier: string;
    recent_reviews: {
      score: number;
      review: string | null;
      created_at: string;
    }[];
  };
  ai_reviews: {
    milestone_name: string;
    verdict: string;
    score: number;
    created_at: string;
  }[];
}

export interface PendingAction {
  type: "proposal" | "submission" | "dispute";
  gig_id: string;
  gig_title: string;
  label: string;
  link: string;
  created_at: string;
}

export interface ActivityEvent {
  id: string;
  type: string;
  message: string;
  gig_id: string;
  created_at: string;
}

export interface ActiveMilestone {
  id: string;
  gig_id: string;
  gig_title: string;
  milestone_name: string;
  budget: string;
  status: string;
  deadline: string | null;
}

export interface ApplicationSummary {
  id: string;
  gig_id: string;
  gig_title: string;
  status: string;
  created_at: string;
}

export function getClientDashboard(): Promise<ClientDashboard> {
  return apiGet<ClientDashboard>("/v1/dashboard/client");
}

export function getFreelancerDashboard(): Promise<FreelancerDashboard> {
  return apiGet<FreelancerDashboard>("/v1/dashboard/freelancer");
}
