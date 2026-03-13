"use client";

import { LogOut } from "lucide-react";
import { AddressDisplay } from "./AddressDisplay";
import { ClusterBadge } from "./ClusterBadge";

interface WalletStatusProps {
  address: string;
  onDisconnect: () => void;
}

export function WalletStatus({ address, onDisconnect }: WalletStatusProps) {
  return (
    <div className="flex items-center gap-2">
      <ClusterBadge />
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
