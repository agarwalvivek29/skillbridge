import { CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { getExplorerUrl } from "@/lib/solana";

interface TxSuccessProps {
  txHash: string;
  onContinue?: () => void;
  className?: string;
}

export function TxSuccess({ txHash, onContinue, className }: TxSuccessProps) {
  return (
    <div
      className={cn("flex flex-col items-center py-8 text-center", className)}
    >
      <CheckCircle className="h-10 w-10 text-success-500" />
      <p className="mt-3 text-sm font-medium text-success-600">
        Transaction confirmed
      </p>
      <a
        href={getExplorerUrl("tx", txHash)}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-1 text-sm text-primary-600 underline hover:text-primary-700"
      >
        View on Solana Explorer
      </a>
      {onContinue && (
        <Button
          variant="primary"
          size="md"
          onClick={onContinue}
          className="mt-4"
        >
          Continue
        </Button>
      )}
    </div>
  );
}
