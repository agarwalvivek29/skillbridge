"use client";

import { useWallet } from "@solana/wallet-adapter-react";
import { useWalletModal } from "@solana/wallet-adapter-react-ui";
import { Wallet } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { WalletStatus } from "./WalletStatus";

export function ConnectButton() {
  const { publicKey, connected, connecting, disconnect } = useWallet();
  const { setVisible } = useWalletModal();

  if (connected && publicKey) {
    return (
      <WalletStatus
        address={publicKey.toBase58()}
        onDisconnect={() => disconnect()}
      />
    );
  }

  return (
    <Button
      variant="web3"
      size="sm"
      loading={connecting}
      onClick={() => setVisible(true)}
    >
      <Wallet className="h-4 w-4" />
      Connect Wallet
    </Button>
  );
}
