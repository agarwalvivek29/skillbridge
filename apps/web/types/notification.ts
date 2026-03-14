/**
 * @proto packages/schema/proto/api/v1/notification.proto — NotificationType enum
 *
 * Subset of proto NotificationType values used in the frontend.
 * Proto values not mapped here:
 *   NOTIFICATION_TYPE_GIG_FUNDED, NOTIFICATION_TYPE_GIG_CANCELLED,
 *   NOTIFICATION_TYPE_GIG_COMPLETED, NOTIFICATION_TYPE_PROPOSAL_REJECTED,
 *   NOTIFICATION_TYPE_FUNDS_RELEASED, NOTIFICATION_TYPE_REVIEW_RECEIVED
 */
export type NotificationType =
  | "PROPOSAL_RECEIVED"
  | "PROPOSAL_ACCEPTED"
  | "SUBMISSION_RECEIVED"
  | "REVIEW_COMPLETE"
  | "MILESTONE_APPROVED"
  | "REVISION_REQUESTED"
  | "DISPUTE_FILED"
  | "DISPUTE_RESOLVED";

/**
 * @proto packages/schema/proto/api/v1/notification.proto — Notification
 *
 * Field mappings:
 *   id         = proto Notification.id
 *   type       = proto Notification.type (enum NotificationType → string union)
 *   created_at = proto Notification.created_at (Timestamp → ISO string)
 *
 * Frontend-only / API-enriched fields:
 *   message  — API-enriched (human-readable text, not in proto; proto stores payload_json)
 *   link     — API-enriched (deep-link URL, derived from payload_json)
 *   read     — API-enriched (boolean; proto uses read_at Timestamp, null = unread)
 *   metadata — API-enriched (parsed from proto payload_json)
 *
 * Proto fields NOT mapped:
 *   Notification.user_id, Notification.payload_json (consumed to produce message/link/metadata)
 */
export interface Notification {
  id: string;
  type: NotificationType;
  message: string;
  link: string | null;
  read: boolean;
  metadata: Record<string, string> | null;
  created_at: string;
}
