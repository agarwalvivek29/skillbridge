"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAccount } from "wagmi";
import { parseEther, isAddress, type Address } from "viem";
import { Wallet, ArrowRight, CheckCircle2, Coins } from "lucide-react";
import { cn } from "@/lib/utils";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Button, Card, Spinner } from "@/components/ui";
import {
  NetworkSwitchPrompt,
  TxPending,
  TxSuccess,
  TxFailed,
} from "@/components/web3";
import { useToast } from "@/hooks/useToast";
import { useTxFlow } from "@/hooks/useTxFlow";
import { fetchGig, fetchEscrowTx, confirmEscrow } from "@/lib/api/gigs";
import type { Gig } from "@/types/gig";

type FundStep = "summary" | "token" | "deposit" | "confirm" | "done";

const FUND_STEPS: { key: FundStep; label: string }[] = [
  { key: "summary", label: "Summary" },
  { key: "token", label: "Token" },
  { key: "deposit", label: "Deposit" },
  { key: "confirm", label: "Confirm" },
];

function FundFlowContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const { isConnected } = useAccount();
  const tx = useTxFlow();

  const [gig, setGig] = useState<Gig | null>(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState<FundStep>("summary");
  const [selectedToken, setSelectedToken] = useState<"ETH" | "USDC">("ETH");
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadGig() {
      try {
        const g = await fetchGig(params.id);
        if (controller.signal.aborted) return;
        setGig(g);
      } catch {
        if (!controller.signal.aborted)
          toast.error("Failed to load gig details");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    loadGig();
    return () => controller.abort();
  }, [params.id, toast]);

  useEffect(() => {
    if (tx.state === "success" && step === "deposit") {
      setStep("confirm");
    }
  }, [tx.state, step]);

  async function handleDeposit() {
    try {
      const escrowTx = await fetchEscrowTx(params.id);
      if (!isAddress(escrowTx.to)) {
        toast.error("Invalid escrow contract address");
        return;
      }
      tx.executeRaw({
        to: escrowTx.to as Address,
        data: escrowTx.data as `0x${string}`,
        value:
          selectedToken === "ETH"
            ? parseEther(escrowTx.value || "0")
            : undefined,
      });
    } catch {
      toast.error("Failed to prepare transaction");
    }
  }

  async function handleConfirmEscrow() {
    if (!tx.txHash) return;
    setConfirming(true);
    setConfirmError(null);
    try {
      await confirmEscrow(params.id, tx.txHash);
      setStep("done");
      toast.success("Escrow funded successfully!");
    } catch {
      setConfirmError(
        "Failed to confirm escrow on SkillBridge. Your on-chain transaction succeeded — click Retry to try again.",
      );
    } finally {
      setConfirming(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!gig) {
    return (
      <div className="py-20 text-center text-neutral-500">Gig not found.</div>
    );
  }

  // Sum in integer units (×1e8) to avoid floating-point accumulation errors
  const total =
    gig.milestones.reduce(
      (sum, m) => sum + Math.round(parseFloat(m.amount || "0") * 1e8),
      0,
    ) / 1e8;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 md:px-6">
      <h1 className="text-2xl font-bold text-neutral-800">Fund Escrow</h1>
      <p className="mt-1 text-sm text-neutral-500">
        Deposit funds to start your gig
      </p>

      {/* Step indicators */}
      <div className="mt-6 flex items-center gap-1">
        {FUND_STEPS.map((s, i) => {
          const currentIdx = FUND_STEPS.findIndex((fs) => fs.key === step);
          const done = step === "done" || i < currentIdx;
          const active = s.key === step;
          return (
            <div key={s.key} className="flex items-center gap-1">
              {i > 0 && (
                <div
                  className={cn(
                    "h-px w-6",
                    done ? "bg-success-500" : "bg-neutral-200",
                  )}
                />
              )}
              <span
                className={cn(
                  "rounded-full px-3 py-1 text-xs font-medium",
                  done && "bg-success-50 text-success-600",
                  active && "bg-primary-50 text-primary-600",
                  !done && !active && "bg-neutral-100 text-neutral-400",
                )}
              >
                {s.label}
              </span>
            </div>
          );
        })}
      </div>

      <NetworkSwitchPrompt />

      <div className="mt-6">
        {/* Step: Summary */}
        {step === "summary" && (
          <Card variant="bordered">
            <h2 className="text-lg font-semibold text-neutral-800">
              {gig.title}
            </h2>
            <div className="mt-4 space-y-2">
              {gig.milestones.map((m, i) => (
                <div
                  key={m.id}
                  className="flex items-center justify-between rounded-md bg-neutral-50 px-3 py-2 text-sm"
                >
                  <span className="text-neutral-600">
                    {i + 1}. {m.title}
                  </span>
                  <span className="font-medium text-neutral-900">
                    {m.amount} {m.currency}
                  </span>
                </div>
              ))}
              <div className="flex items-center justify-between border-t border-neutral-200 pt-3">
                <span className="font-semibold text-neutral-700">Total</span>
                <span className="text-xl font-bold text-neutral-900">
                  {total.toFixed(2)} {gig.currency || "USDC"}
                </span>
              </div>
            </div>
            <div className="mt-6">
              <Button onClick={() => setStep("token")} className="w-full">
                Continue <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </div>
          </Card>
        )}

        {/* Step: Token selection */}
        {step === "token" && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-neutral-800">
              Select Payment Token
            </h2>
            <div className="grid grid-cols-2 gap-4">
              {(["ETH", "USDC"] as const).map((token) => (
                <button
                  key={token}
                  onClick={() => setSelectedToken(token)}
                  className={cn(
                    "flex flex-col items-center gap-2 rounded-lg border-2 p-6 transition-colors",
                    selectedToken === token
                      ? "border-primary-500 bg-primary-50"
                      : "border-neutral-200 hover:border-neutral-300",
                  )}
                >
                  <Coins className="h-8 w-8 text-neutral-600" />
                  <span className="font-semibold text-neutral-800">
                    {token}
                  </span>
                </button>
              ))}
            </div>
            <Button onClick={() => setStep("deposit")} className="w-full">
              Continue with {selectedToken}
            </Button>
          </div>
        )}

        {/* Step: Deposit */}
        {step === "deposit" && (
          <div className="space-y-4">
            {tx.state === "idle" && (
              <Card variant="bordered">
                <div className="flex flex-col items-center gap-4 py-4">
                  <Wallet className="h-12 w-12 text-web3-500" />
                  <div className="text-center">
                    <h2 className="text-lg font-semibold text-neutral-800">
                      Deposit {total.toFixed(2)} {selectedToken}
                    </h2>
                    <p className="mt-1 text-sm text-neutral-500">
                      This will create a secure escrow for your gig
                    </p>
                  </div>
                  <Button
                    variant="web3"
                    onClick={handleDeposit}
                    disabled={!isConnected}
                    className="w-full"
                  >
                    Deposit to Escrow
                  </Button>
                </div>
              </Card>
            )}
            {(tx.state === "pending" || tx.state === "confirming") && (
              <TxPending txHash={tx.txHash} />
            )}
            {tx.state === "error" && (
              <TxFailed
                error={tx.error || "Transaction failed"}
                onRetry={() => {
                  tx.reset();
                  handleDeposit();
                }}
              />
            )}
          </div>
        )}

        {/* Step: Confirm */}
        {step === "confirm" && tx.txHash && (
          <div className="space-y-4">
            <TxSuccess txHash={tx.txHash} />
            {confirmError && (
              <div className="rounded-lg bg-error-50 p-3 text-sm text-error-700">
                {confirmError}
              </div>
            )}
            <Button
              onClick={handleConfirmEscrow}
              loading={confirming}
              className="w-full"
            >
              <CheckCircle2 className="mr-1 h-4 w-4" />
              {confirmError ? "Retry Confirm" : "Confirm Escrow on SkillBridge"}
            </Button>
          </div>
        )}

        {/* Step: Done */}
        {step === "done" && (
          <Card variant="bordered">
            <div className="flex flex-col items-center gap-4 py-8">
              <div className="rounded-full bg-success-50 p-4">
                <CheckCircle2 className="h-10 w-10 text-success-500" />
              </div>
              <h2 className="text-xl font-bold text-neutral-800">
                Escrow Funded!
              </h2>
              <p className="text-center text-sm text-neutral-500">
                Your gig is now live. Freelancers can start submitting
                proposals.
              </p>
              <Button onClick={() => router.push(`/gigs/${params.id}/manage`)}>
                Manage Gig
              </Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

export default function FundEscrowPage() {
  return (
    <AuthGuard>
      <FundFlowContent />
    </AuthGuard>
  );
}
