import { Fuel } from "lucide-react";
import { LAMPORTS_PER_SOL } from "@solana/web3.js";
import { cn } from "@/lib/utils";

interface GasEstimateProps {
  /** Estimated fee in lamports */
  feeLamports: bigint;
  solUsdPrice?: number;
  className?: string;
}

export function GasEstimate({
  feeLamports,
  solUsdPrice,
  className,
}: GasEstimateProps) {
  const feeSol = Number(feeLamports) / LAMPORTS_PER_SOL;
  const feeSolFormatted = feeSol.toFixed(6);
  const feeUsd = solUsdPrice ? (feeSol * solUsdPrice).toFixed(4) : null;

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm",
        className,
      )}
    >
      <Fuel className="h-4 w-4 text-neutral-400" />
      <span className="text-neutral-600">
        Est. fee: <span className="font-medium">{feeSolFormatted} SOL</span>
        {feeUsd && <span className="text-neutral-400"> (~${feeUsd})</span>}
      </span>
    </div>
  );
}
