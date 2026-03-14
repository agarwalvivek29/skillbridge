/**
 * Frontend-only type — no direct proto equivalent.
 * Predefined tag options for ratings. Proto Review has no tags field.
 */
export type RatingTag =
  | "Great communication"
  | "High quality work"
  | "Delivered on time"
  | "Would hire again";

/**
 * @proto packages/schema/proto/api/v1/reputation.proto — Reputation
 *        packages/schema/proto/api/v1/review.proto — Review
 *
 * Field mappings (from review.proto Review):
 *   id         = proto Review.id
 *   gig_id     = proto Review.gig_id
 *   rater_id   ← proto Review.reviewer_id
 *   ratee_id   ← proto Review.reviewee_id
 *   score      ← proto Review.rating
 *   review     ← proto Review.comment
 *   created_at = proto Review.created_at (Timestamp → ISO string)
 *
 * Frontend-only / API-enriched fields:
 *   tags — API-enriched (RatingTag[], not in proto Review)
 *
 * Proto fields NOT mapped:
 *   Review.is_visible
 */
export interface Rating {
  id: string;
  gig_id: string;
  rater_id: string;
  ratee_id: string;
  score: number;
  review: string | null;
  tags: RatingTag[];
  created_at: string;
}

/**
 * @proto packages/schema/proto/api/v1/review.proto — CreateReviewRequest
 *
 * Field mappings:
 *   gig_id  = proto CreateReviewRequest.gig_id
 *   score   ← proto CreateReviewRequest.rating
 *   review  ← proto CreateReviewRequest.comment
 *
 * Frontend-only fields:
 *   ratee_id — API-enriched (proto infers reviewee from gig roles)
 *   tags     — not in proto request
 */
export interface CreateRatingPayload {
  gig_id: string;
  ratee_id: string;
  score: number;
  review?: string;
  tags: RatingTag[];
}

/**
 * Frontend-only composite type — no direct proto equivalent.
 * Aggregates both parties' reviews for the blind-reveal UI.
 * Proto Review.is_visible controls the reveal logic server-side.
 */
export interface MutualRatings {
  mine: Rating | null;
  theirs: Rating | null;
  revealed: boolean;
}
