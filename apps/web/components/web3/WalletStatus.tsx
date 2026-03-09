"use client";

import { useAccount } from "wagmi";
import { LogOut } from "lucide-react";
import { AddressDisplay } from "./AddressDisplay";
import { ChainBadge } from "./ChainBadge";

interface WalletStatusProps {
  address: `0x${string}`;
  onDisconnect: () => void;
}

export function WalletStatus({ address, onDisconnect }: WalletStatusProps) {
  const { chain } = useAccount();

  return (
    <div className="flex items-center gap-2">
      {chain && <ChainBadge chainId={chain.id} chainName={chain.name} />}
      <AddressDisplay address={address} />
      <button
        onClick={onDisconnect}
        className="rounded-md p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
        aria-label="Disconnect wallet"
      >
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );
}
