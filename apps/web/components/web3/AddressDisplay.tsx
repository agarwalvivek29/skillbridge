"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface AddressDisplayProps {
  address: string;
  className?: string;
}

function truncateAddress(addr: string) {
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

export function AddressDisplay({ address, className }: AddressDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className={cn(
        "group inline-flex items-center gap-1.5 rounded-full border border-web3-200 bg-web3-50 px-2 py-0.5 font-mono text-xs transition-colors hover:bg-web3-100",
        className,
      )}
      title="Click to copy address"
    >
      <span>{truncateAddress(address)}</span>
      {copied ? (
        <Check className="h-3 w-3 text-success-500" />
      ) : (
        <Copy className="h-3 w-3 text-neutral-400 opacity-0 transition-opacity group-hover:opacity-100" />
      )}
    </button>
  );
}
