import { apiGet } from "./client";
import type { Gig, Milestone } from "@/types/gig";

export interface WorkspaceData {
  gig: Gig;
  submissions: WorkspaceSubmission[];
}

export interface WorkspaceSubmission {
  id: string;
  milestone_id: string;
  repo_url: string | null;
  file_keys: string[];
  notes: string | null;
  review_verdict: string | null;
  review_score: number | null;
  created_at: string;
}

export function getWorkspace(gigId: string): Promise<WorkspaceData> {
  return apiGet<WorkspaceData>(`/v1/gigs/${gigId}/workspace`);
}
