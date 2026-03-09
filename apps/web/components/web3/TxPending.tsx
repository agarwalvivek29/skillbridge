import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface TxPendingProps {
  txHash?: string;
  inline?: boolean;
  className?: string;
}

function getExplorerUrl(hash: string) {
  const chainId = Number(process.env.NEXT_PUBLIC_BASE_CHAIN_ID ?? 84532);
  const base =
    chainId === 8453 ? "https://basescan.org" : "https://sepolia.basescan.org";
  return `${base}/tx/${hash}`;
}

export function TxPending({ txHash, inline, className }: TxPendingProps) {
  if (inline) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 text-sm text-neutral-500",
          className,
        )}
      >
        <Loader2 className="h-4 w-4 animate-spin text-web3-500" />
        Pending...
      </span>
    );
  }

  return (
    <div
      className={cn("flex flex-col items-center py-8 text-center", className)}
    >
      <Loader2 className="h-8 w-8 animate-spin text-web3-500" />
      <p className="mt-3 text-sm text-neutral-500">Transaction pending...</p>
      {txHash && (
        <a
          href={getExplorerUrl(txHash)}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 text-sm text-primary-600 underline hover:text-primary-700"
        >
          View on BaseScan
        </a>
      )}
    </div>
  );
}
