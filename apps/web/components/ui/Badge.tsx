import { cn } from "@/lib/utils";

const variantStyles = {
  default: "bg-neutral-100 text-neutral-600 border-neutral-300",
  primary: "bg-primary-50 text-primary-700 border-primary-200",
  success: "bg-success-50 text-[#166534] border-[#BBF7D0]",
  error: "bg-error-50 text-[#991B1B] border-[#FECACA]",
  warning: "bg-warning-50 text-[#92400E] border-[#FDE68A]",
  info: "bg-info-50 text-info-600 border-primary-200",
  web3: "bg-web3-50 text-[#5B21B6] border-web3-200",
} as const;

interface BadgeProps {
  variant?: keyof typeof variantStyles;
  children: React.ReactNode;
  className?: string;
}

export function Badge({
  variant = "default",
  children,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
