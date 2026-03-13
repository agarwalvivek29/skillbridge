import { cn } from "@/lib/utils";
import { getSolanaCluster } from "@/lib/solana";

interface ClusterBadgeProps {
  className?: string;
}

const CLUSTER_LABELS: Record<string, string> = {
  "mainnet-beta": "Mainnet",
  devnet: "Devnet",
  testnet: "Testnet",
  localnet: "Localnet",
};

export function ClusterBadge({ className }: ClusterBadgeProps) {
  const cluster = getSolanaCluster();
  const isMainnet = cluster === "mainnet-beta";
  const label = CLUSTER_LABELS[cluster] ?? cluster;

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
      {label}
    </span>
  );
}
