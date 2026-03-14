/**
 * @proto packages/schema/proto/api/v1/submission.proto — Submission
 *
 * Field mappings:
 *   id              = proto Submission.id
 *   milestone_id    = proto Submission.milestone_id
 *   freelancer_id   = proto Submission.freelancer_id
 *   repo_url        = proto Submission.repo_url
 *   file_keys       = proto Submission.file_keys
 *   notes           = proto Submission.notes
 *   revision_number = proto Submission.revision_number
 *   status          = proto Submission.status (enum SubmissionStatus → string)
 *   created_at      = proto Submission.created_at (Timestamp → ISO string)
 *
 * Proto fields NOT mapped:
 *   Submission.previous_submission_id, Submission.updated_at
 */
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

/**
 * @proto packages/schema/proto/api/v1/review.proto — Review
 *
 * Note: the proto entity is named "Review" (mutual rating review), but this
 * frontend type represents an AI code review report. The mapping is loose —
 * this type is primarily shaped by the ai-reviewer service response.
 *
 * Field mappings:
 *   id            = proto Review.id
 *   submission_id — API-enriched (not directly on proto Review; review is per-gig in proto)
 *   verdict       — API-enriched (mapped from ai-reviewer output, not proto Review)
 *   score         ← proto Review.rating (reinterpreted as AI score)
 *   body          ← proto Review.comment
 *   created_at    = proto Review.created_at (Timestamp → ISO string)
 *
 * Frontend-only / API-enriched fields:
 *   submission_id — API-enriched (links review to a specific submission)
 *   verdict       — API-enriched ("PASS" | "FAIL" | "PENDING", from ai-reviewer)
 *   model_version — API-enriched (AI model version, not in proto)
 */
export interface ReviewReport {
  id: string;
  submission_id: string;
  verdict: "PASS" | "FAIL" | "PENDING";
  score: number;
  body: string;
  model_version: string;
  created_at: string;
}

/**
 * @proto packages/schema/proto/api/v1/milestone.proto — Milestone
 *        packages/schema/proto/api/v1/submission.proto — Submission
 *        packages/schema/proto/api/v1/review.proto — Review
 *
 * Composite type joining milestone, its submissions, and latest review.
 *
 * Field mappings (from milestone.proto Milestone):
 *   id, gig_id, title, description, amount, status, order, due_date
 *   acceptance_criteria = proto Milestone.acceptance_criteria
 *
 * Frontend-only / API-enriched fields:
 *   gig_title          — API-enriched (joined from Gig.title)
 *   currency           — API-enriched (from parent Gig.currency)
 *   client_id          — API-enriched (from parent Gig.client_id)
 *   freelancer_id      — API-enriched (from parent Gig.freelancer_id)
 *   revision_feedback  — API-enriched (from RequestRevisionRequest.feedback)
 *   submissions        — API-enriched (nested Submission[])
 *   latest_review      — API-enriched (nested ReviewReport | null)
 */
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

/**
 * @proto packages/schema/proto/contracts/v1/escrow.proto — ReleaseMilestoneFundsResponse
 *
 * Frontend-only / API-enriched fields:
 *   serialized_tx — API-enriched (base64-encoded Solana transaction, not in proto)
 */
export interface ReleaseTx {
  /** Base64-encoded serialized Solana transaction */
  serialized_tx: string;
}
