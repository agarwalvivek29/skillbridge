import { apiGet, apiPost, apiPut, apiDelete } from "./client";
import type { Gig, GigListResponse } from "@/types/gig";
import type { EscrowTx } from "@/types/escrow";
import type { Proposal, ProposalListResponse } from "@/types/proposal";

export interface GigQueryParams {
  page?: number;
  page_size?: number;
  sort?: string;
  search?: string;
  category?: string;
  status?: string;
  min_budget?: string;
  max_budget?: string;
  skills?: string[];
}

export function fetchGigs(
  params: GigQueryParams = {},
): Promise<GigListResponse> {
  const query = new URLSearchParams();
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));
  if (params.sort) query.set("sort", params.sort);
  if (params.search) query.set("search", params.search);
  if (params.category) query.set("category", params.category);
  if (params.status) query.set("status", params.status);
  if (params.min_budget) query.set("min_budget", params.min_budget);
  if (params.max_budget) query.set("max_budget", params.max_budget);
  if (params.skills?.length) query.set("skills", params.skills.join(","));

  const qs = query.toString();
  return apiGet<GigListResponse>(`/v1/gigs${qs ? `?${qs}` : ""}`);
}

export function fetchGig(id: string): Promise<Gig> {
  return apiGet<Gig>(`/v1/gigs/${id}`);
}

export function fetchSimilarGigs(
  gigId: string,
  limit = 3,
): Promise<GigListResponse> {
  return apiGet<GigListResponse>(`/v1/gigs?exclude=${gigId}&limit=${limit}`);
}

export interface CreateGigPayload {
  title: string;
  description: string;
  category: string;
  skills: string[];
  deadline: string | null;
  milestones: {
    title: string;
    description: string;
    acceptance_criteria: string;
    amount: string;
    currency: string;
  }[];
}

// Solana devnet USDC mint address
const USDC_DEVNET_MINT = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU";

export function createGig(payload: CreateGigPayload): Promise<Gig> {
  // Map frontend shape to API shape
  const currency = payload.milestones[0]?.currency || "USDC";
  // Convert human-readable amounts to smallest unit (USDC has 6 decimals, SOL has 9)
  const decimals = currency === "USDC" ? 1_000_000 : 1_000_000_000;
  const totalAmount = payload.milestones
    .reduce(
      (sum, m) => sum + Math.round(parseFloat(m.amount || "0") * decimals),
      0,
    )
    .toString();

  return apiPost<Gig>("/v1/gigs", {
    title: payload.title,
    description: payload.description,
    total_amount: totalAmount,
    currency,
    token_address: currency === "USDC" ? USDC_DEVNET_MINT : undefined,
    tags: payload.category ? [payload.category] : [],
    required_skills: payload.skills,
    deadline: payload.deadline || undefined,
    milestones: payload.milestones.map((m, i) => ({
      title: m.title,
      description: m.description,
      acceptance_criteria: m.acceptance_criteria,
      amount: Math.round(parseFloat(m.amount || "0") * decimals).toString(),
      order: i + 1,
    })),
  });
}

export function updateGig(
  id: string,
  payload: Partial<CreateGigPayload>,
): Promise<Gig> {
  return apiPut<Gig>(`/v1/gigs/${id}`, payload);
}

export function deleteGig(id: string): Promise<void> {
  return apiDelete<void>(`/v1/gigs/${id}`);
}

export function fetchEscrowTx(gigId: string): Promise<EscrowTx> {
  return apiGet<EscrowTx>(`/v1/gigs/${gigId}/escrow-tx`);
}

export function confirmEscrow(gigId: string, txHash: string): Promise<Gig> {
  return apiPost<Gig>(`/v1/gigs/${gigId}/confirm-escrow`, { tx_hash: txHash });
}

export function fetchGigProposals(
  gigId: string,
): Promise<ProposalListResponse> {
  return apiGet<ProposalListResponse>(`/v1/gigs/${gigId}/proposals`);
}

export interface SubmitProposalPayload {
  cover_letter: string;
  proposed_rate?: string;
  timeline: { milestone_id: string; estimated_delivery: string }[];
  attachments?: string[];
}

export function submitProposal(
  gigId: string,
  payload: SubmitProposalPayload,
): Promise<Proposal> {
  return apiPost<Proposal>(`/v1/gigs/${gigId}/proposals`, payload);
}

export function fetchMyProposal(gigId: string): Promise<Proposal | null> {
  return apiGet<Proposal | null>(`/v1/gigs/${gigId}/proposals/mine`);
}

export function acceptProposal(proposalId: string): Promise<Proposal> {
  return apiPost<Proposal>(`/v1/proposals/${proposalId}/accept`);
}

export function rejectProposal(
  proposalId: string,
  message?: string,
): Promise<Proposal> {
  return apiPost<Proposal>(`/v1/proposals/${proposalId}/reject`, { message });
}

export interface GigSubmission {
  id: string;
  milestone_id: string;
  milestone_title: string;
  freelancer_id: string;
  repo_url: string | null;
  file_urls: string[];
  notes: string;
  status: string;
  created_at: string;
}

export function fetchGigSubmissions(gigId: string): Promise<GigSubmission[]> {
  return apiGet<GigSubmission[]>(`/v1/gigs/${gigId}/submissions`);
}
