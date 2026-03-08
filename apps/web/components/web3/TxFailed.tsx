import { XCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

interface TxFailedProps {
  error: string;
  onRetry?: () => void;
  className?: string;
}

export function TxFailed({ error, onRetry, className }: TxFailedProps) {
  return (
    <div
      className={cn("flex flex-col items-center py-8 text-center", className)}
    >
      <XCircle className="h-10 w-10 text-error-500" />
      <p className="mt-3 text-sm font-medium text-error-600">
        Transaction failed
      </p>
      <p className="mt-1 max-w-sm text-sm text-neutral-500">{error}</p>
      {onRetry && (
        <Button variant="outline" size="md" onClick={onRetry} className="mt-4">
          Try Again
        </Button>
      )}
    </div>
  );
}
