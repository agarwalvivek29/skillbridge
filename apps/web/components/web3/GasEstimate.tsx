import { Fuel } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatEther } from "viem";

interface GasEstimateProps {
  gasEstimate: bigint;
  gasPrice: bigint;
  ethUsdPrice?: number;
  className?: string;
}

export function GasEstimate({
  gasEstimate,
  gasPrice,
  ethUsdPrice,
  className,
}: GasEstimateProps) {
  const costWei = gasEstimate * gasPrice;
  const costEth = formatEther(costWei);
  const costEthFormatted = parseFloat(costEth).toFixed(6);
  const costUsd = ethUsdPrice
    ? (parseFloat(costEth) * ethUsdPrice).toFixed(2)
    : null;

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm",
        className,
      )}
    >
      <Fuel className="h-4 w-4 text-neutral-400" />
      <span className="text-neutral-600">
        Est. gas: <span className="font-medium">{costEthFormatted} ETH</span>
        {costUsd && <span className="text-neutral-400"> (~${costUsd})</span>}
      </span>
    </div>
  );
}
