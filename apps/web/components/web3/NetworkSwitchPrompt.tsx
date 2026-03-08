"use client";

import { useAccount, useSwitchChain } from "wagmi";
import { baseSepolia } from "wagmi/chains";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";

const TARGET_CHAIN_ID = Number(
  process.env.NEXT_PUBLIC_BASE_CHAIN_ID ?? baseSepolia.id,
) as 8453 | 84532;

export function NetworkSwitchPrompt() {
  const { chain, isConnected } = useAccount();
  const { switchChain, isPending } = useSwitchChain();

  if (!isConnected || !chain || chain.id === TARGET_CHAIN_ID) return null;

  return (
    <div className="flex items-center justify-between gap-4 border-b border-warning-500 bg-warning-50 px-4 py-3">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-warning-500" />
        <p className="text-sm font-medium text-[#92400E]">
          Wrong network detected. Please switch to Base.
        </p>
      </div>
      <Button
        variant="primary"
        size="sm"
        loading={isPending}
        onClick={() => switchChain({ chainId: TARGET_CHAIN_ID })}
      >
        Switch Network
      </Button>
    </div>
  );
}
