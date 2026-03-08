import { Download } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function InstallWalletPrompt() {
  return (
    <div className="flex flex-col items-center rounded-lg border border-neutral-200 bg-white p-8 text-center">
      <Download className="h-10 w-10 text-web3-500" />
      <h3 className="mt-4 text-lg font-semibold text-neutral-800">
        No Wallet Detected
      </h3>
      <p className="mt-1 text-sm text-neutral-500">
        You need a Web3 wallet to use SkillBridge. Install MetaMask to get
        started.
      </p>
      <a
        href="https://metamask.io/download/"
        target="_blank"
        rel="noopener noreferrer"
      >
        <Button variant="web3" size="md" className="mt-4">
          Install MetaMask
        </Button>
      </a>
    </div>
  );
}
