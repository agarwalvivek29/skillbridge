import { apiGet, apiPost } from "./client";
import type {
  Submission,
  MilestoneDetail,
  ReviewReport,
  ReleaseTx,
} from "@/types/submission";

export function fetchMilestone(milestoneId: string): Promise<MilestoneDetail> {
  return apiGet<MilestoneDetail>(`/v1/milestones/${milestoneId}`);
}

export interface CreateSubmissionPayload {
  milestone_id: string;
  repo_url?: string;
  file_keys?: string[];
  notes?: string;
}

export function createSubmission(
  payload: CreateSubmissionPayload,
): Promise<Submission> {
  return apiPost<Submission>("/v1/submissions", payload);
}

export function getUploadUrl(
  filename: string,
): Promise<{ upload_url: string; file_key: string }> {
  return apiGet<{ upload_url: string; file_key: string }>(
    `/v1/submissions/upload-url?filename=${encodeURIComponent(filename)}`,
  );
}

export function fetchReviewReport(submissionId: string): Promise<ReviewReport> {
  return apiGet<ReviewReport>(`/v1/submissions/${submissionId}/review-report`);
}

export function getReleaseTx(milestoneId: string): Promise<ReleaseTx> {
  return apiGet<ReleaseTx>(`/v1/milestones/${milestoneId}/release-tx`);
}

export function confirmRelease(
  milestoneId: string,
  txHash: string,
): Promise<void> {
  return apiPost<void>(`/v1/milestones/${milestoneId}/confirm-release`, {
    tx_hash: txHash,
  });
}

export function requestRevision(
  milestoneId: string,
  feedback: string,
): Promise<void> {
  return apiPost<void>(`/v1/milestones/${milestoneId}/revision`, {
    feedback,
  });
}
