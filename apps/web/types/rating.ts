export type RatingTag =
  | "Great communication"
  | "High quality work"
  | "Delivered on time"
  | "Would hire again";

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

export interface CreateRatingPayload {
  gig_id: string;
  ratee_id: string;
  score: number;
  review?: string;
  tags: RatingTag[];
}

export interface MutualRatings {
  mine: Rating | null;
  theirs: Rating | null;
  revealed: boolean;
}
