"use client";

import { useWallet } from "@solana/wallet-adapter-react";
import { AlertTriangle } from "lucide-react";
import { getSolanaCluster } from "@/lib/solana";

const CLUSTER_LABELS: Record<string, string> = {
  "mainnet-beta": "Mainnet",
  devnet: "Devnet",
  testnet: "Testnet",
  localnet: "Localnet",
};

export function NetworkSwitchPrompt() {
  const { connected } = useWallet();
  const cluster = getSolanaCluster();

  if (!connected) return null;

  // Only show a warning when running on localnet — in production the wallet
  // connects to whatever RPC the app provides, so there is no "wrong network"
  // in the EVM sense.  We keep this component as an informational banner when
  // the app is configured for localnet so developers are aware.
  if (cluster !== "localnet") return null;

  return (
    <div className="flex items-center justify-between gap-4 border-b border-warning-500 bg-warning-50 px-4 py-3">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-warning-500" />
        <p className="text-sm font-medium text-[#92400E]">
          Connected to {CLUSTER_LABELS[cluster] ?? cluster}. Transactions will
          not appear on mainnet.
        </p>
      </div>
    </div>
  );
}
