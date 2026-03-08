import { cn } from "@/lib/utils";

const statusStyles: Record<
  string,
  { bg: string; text: string; border: string; dot: string }
> = {
  DRAFT: {
    bg: "bg-neutral-100",
    text: "text-neutral-600",
    border: "border-neutral-300",
    dot: "bg-neutral-400",
  },
  OPEN: {
    bg: "bg-primary-50",
    text: "text-primary-700",
    border: "border-primary-200",
    dot: "bg-primary-500",
  },
  PENDING: {
    bg: "bg-neutral-100",
    text: "text-neutral-600",
    border: "border-neutral-300",
    dot: "bg-neutral-400",
  },
  SUBMITTED: {
    bg: "bg-primary-50",
    text: "text-primary-700",
    border: "border-primary-200",
    dot: "bg-primary-500",
  },
  UNDER_REVIEW: {
    bg: "bg-warning-50",
    text: "text-warning-700",
    border: "border-warning-200",
    dot: "bg-warning-500",
  },
  APPROVED: {
    bg: "bg-success-50",
    text: "text-success-800",
    border: "border-success-200",
    dot: "bg-success-500",
  },
  PAID: {
    bg: "bg-[#ECFDF5]",
    text: "text-[#065F46]",
    border: "border-[#A7F3D0]",
    dot: "bg-[#10B981]",
  },
  REVISION_REQUESTED: {
    bg: "bg-[#FFF7ED]",
    text: "text-[#9A3412]",
    border: "border-[#FED7AA]",
    dot: "bg-[#F97316]",
  },
  DISPUTED: {
    bg: "bg-error-50",
    text: "text-error-800",
    border: "border-error-200",
    dot: "bg-error-500",
  },
  IN_PROGRESS: {
    bg: "bg-primary-50",
    text: "text-primary-700",
    border: "border-primary-200",
    dot: "bg-primary-500",
  },
  COMPLETED: {
    bg: "bg-success-50",
    text: "text-success-800",
    border: "border-success-200",
    dot: "bg-success-500",
  },
  CANCELLED: {
    bg: "bg-neutral-100",
    text: "text-neutral-500",
    border: "border-neutral-300",
    dot: "bg-neutral-400",
  },
  ACCEPTED: {
    bg: "bg-success-50",
    text: "text-success-800",
    border: "border-success-200",
    dot: "bg-success-500",
  },
  REJECTED: {
    bg: "bg-error-50",
    text: "text-error-800",
    border: "border-error-200",
    dot: "bg-error-500",
  },
  WITHDRAWN: {
    bg: "bg-neutral-100",
    text: "text-neutral-500",
    border: "border-neutral-300",
    dot: "bg-neutral-400",
  },
  DISCUSSION: {
    bg: "bg-warning-50",
    text: "text-warning-700",
    border: "border-warning-200",
    dot: "bg-warning-500",
  },
  ARBITRATION: {
    bg: "bg-web3-50",
    text: "text-web3-800",
    border: "border-web3-200",
    dot: "bg-web3-500",
  },
  RESOLVED: {
    bg: "bg-success-50",
    text: "text-success-800",
    border: "border-success-200",
    dot: "bg-success-500",
  },
};

const fallback = {
  bg: "bg-neutral-100",
  text: "text-neutral-600",
  border: "border-neutral-300",
  dot: "bg-neutral-400",
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const style = statusStyles[status] ?? fallback;

  return (
    <span
      role="status"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium uppercase",
        style.bg,
        style.text,
        style.border,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", style.dot)} />
      {status.replace(/_/g, " ")}
    </span>
  );
}
