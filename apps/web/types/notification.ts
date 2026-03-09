// View model for API JSON responses. Proto source: packages/schema/proto/api/v1/notification.proto
// Enum re-exported from @/types/proto (aliased to avoid conflict with local string union).

export { NotificationType as ProtoNotificationType } from "./proto";

export type NotificationType =
  | "PROPOSAL_RECEIVED"
  | "PROPOSAL_ACCEPTED"
  | "SUBMISSION_RECEIVED"
  | "REVIEW_COMPLETE"
  | "MILESTONE_APPROVED"
  | "REVISION_REQUESTED"
  | "DISPUTE_FILED"
  | "DISPUTE_RESOLVED";

export interface Notification {
  id: string;
  type: NotificationType;
  message: string;
  link: string | null;
  read: boolean;
  metadata: Record<string, string> | null;
  created_at: string;
}
