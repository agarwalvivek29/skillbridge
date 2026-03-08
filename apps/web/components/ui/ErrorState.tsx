import { type LucideIcon, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./Button";

interface ErrorStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function ErrorState({
  icon: Icon = AlertTriangle,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn("flex flex-col items-center py-12 text-center", className)}
    >
      <Icon className="h-12 w-12 text-error-500" />
      <h3 className="mt-4 text-lg font-semibold text-neutral-800">{title}</h3>
      {description && (
        <p className="mt-1 text-sm text-neutral-500">{description}</p>
      )}
      {actionLabel && onAction && (
        <Button variant="outline" size="md" onClick={onAction} className="mt-4">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
