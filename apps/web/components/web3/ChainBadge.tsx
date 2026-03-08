import { cn } from "@/lib/utils";
import { base } from "wagmi/chains";

interface ChainBadgeProps {
  chainId: number;
  chainName: string;
  className?: string;
}

export function ChainBadge({ chainId, chainName, className }: ChainBadgeProps) {
  const isMainnet = chainId === base.id;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-web3-200 bg-web3-50 px-2 py-0.5 text-xs font-medium",
        className,
      )}
    >
      <span
        className={cn(
          "h-2 w-2 rounded-full",
          isMainnet ? "bg-success-500" : "bg-warning-500",
        )}
      />
      {chainName}
    </span>
  );
}
