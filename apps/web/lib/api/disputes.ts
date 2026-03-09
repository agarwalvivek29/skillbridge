import { apiGet, apiPost } from "./client";
import type {
  Dispute,
  CreateDisputePayload,
  SubmitEvidencePayload,
  ArbitrationCase,
  ArbitrationVote,
  CastVotePayload,
} from "@/types/dispute";

export function createDispute(payload: CreateDisputePayload): Promise<Dispute> {
  return apiPost<Dispute>("/v1/disputes", payload);
}

export function fetchDispute(disputeId: string): Promise<Dispute> {
  return apiGet<Dispute>(`/v1/disputes/${disputeId}`);
}

export function submitEvidence(
  disputeId: string,
  payload: SubmitEvidencePayload,
): Promise<void> {
  return apiPost<void>(`/v1/disputes/${disputeId}/evidence`, payload);
}

export function fetchArbitrationQueue(
  filter: "assigned" | "all",
): Promise<ArbitrationCase[]> {
  return apiGet<ArbitrationCase[]>(
    `/v1/arbitration?filter=${encodeURIComponent(filter)}`,
  );
}

export function fetchArbitrationDetail(disputeId: string): Promise<Dispute> {
  return apiGet<Dispute>(`/v1/arbitration/${disputeId}`);
}

export function fetchVotes(disputeId: string): Promise<ArbitrationVote[]> {
  return apiGet<ArbitrationVote[]>(`/v1/disputes/${disputeId}/votes`);
}

export function castVote(
  disputeId: string,
  payload: CastVotePayload,
): Promise<void> {
  return apiPost<void>(`/v1/disputes/${disputeId}/vote`, payload);
}
