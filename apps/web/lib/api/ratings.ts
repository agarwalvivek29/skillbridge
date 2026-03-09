import { apiGet, apiPost } from "./client";
import type {
  CreateRatingPayload,
  MutualRatings,
  Rating,
} from "@/types/rating";

export function createRating(payload: CreateRatingPayload): Promise<Rating> {
  return apiPost<Rating>("/v1/ratings", payload);
}

export function fetchMutualRatings(gigId: string): Promise<MutualRatings> {
  return apiGet<MutualRatings>(`/v1/ratings/gig/${gigId}/mutual`);
}
