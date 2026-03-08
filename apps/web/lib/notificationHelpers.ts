import {
  FileText,
  CheckCircle,
  Upload,
  Shield,
  DollarSign,
  RefreshCw,
  AlertTriangle,
  Scale,
  type LucideIcon,
} from "lucide-react";
import type { NotificationType } from "@/types/notification";

const iconMap: Record<NotificationType, LucideIcon> = {
  PROPOSAL_RECEIVED: FileText,
  PROPOSAL_ACCEPTED: CheckCircle,
  SUBMISSION_RECEIVED: Upload,
  REVIEW_COMPLETE: Shield,
  MILESTONE_APPROVED: DollarSign,
  REVISION_REQUESTED: RefreshCw,
  DISPUTE_FILED: AlertTriangle,
  DISPUTE_RESOLVED: Scale,
};

const labelMap: Record<NotificationType, string> = {
  PROPOSAL_RECEIVED: "New proposal",
  PROPOSAL_ACCEPTED: "Proposal accepted",
  SUBMISSION_RECEIVED: "New submission",
  REVIEW_COMPLETE: "AI review complete",
  MILESTONE_APPROVED: "Milestone approved",
  REVISION_REQUESTED: "Revision requested",
  DISPUTE_FILED: "Dispute filed",
  DISPUTE_RESOLVED: "Dispute resolved",
};

export function notificationIcon(type: NotificationType): LucideIcon {
  return iconMap[type] ?? FileText;
}

export function notificationLabel(type: NotificationType): string {
  return labelMap[type] ?? type;
}
