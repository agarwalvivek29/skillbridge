"use client";

import { useAccount, useConnect, useDisconnect } from "wagmi";
import { Wallet } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { WalletStatus } from "./WalletStatus";

export function ConnectButton() {
  const { address, isConnected } = useAccount();
  const { connect, connectors, isPending } = useConnect();
  const { disconnect } = useDisconnect();

  if (isConnected && address) {
    return <WalletStatus address={address} onDisconnect={() => disconnect()} />;
  }

  return (
    <Button
      variant="web3"
      size="sm"
      loading={isPending}
      onClick={() => {
        const connector = connectors[0];
        if (connector) connect({ connector });
      }}
    >
      <Wallet className="h-4 w-4" />
      Connect Wallet
    </Button>
  );
}
