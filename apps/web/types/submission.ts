// View model for API JSON responses. Proto source: packages/schema/proto/api/v1/submission.proto
// Enums re-exported from @/types/proto; enriched fields are web-layer only.

export { SubmissionStatus, MilestoneStatus } from "./proto";

export interface Submission {
  id: string;
  milestone_id: string;
  freelancer_id: string;
  repo_url: string | null;
  file_keys: string[];
  notes: string | null;
  revision_number: number;
  status: string;
  created_at: string;
}

export interface ReviewReport {
  id: string;
  submission_id: string;
  verdict: "PASS" | "FAIL" | "PENDING";
  score: number;
  body: string;
  model_version: string;
  created_at: string;
}

export interface MilestoneDetail {
  id: string;
  gig_id: string;
  gig_title: string;
  title: string;
  description: string;
  acceptance_criteria: string | null;
  amount: string;
  currency: string;
  status: string;
  order: number;
  due_date: string | null;
  client_id: string;
  freelancer_id: string | null;
  revision_feedback: string | null;
  submissions: Submission[];
  latest_review: ReviewReport | null;
}

export interface ReleaseTx {
  to: string;
  data: string;
  value: string;
}
