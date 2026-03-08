"use client";

import { useState, useCallback, useEffect } from "react";
import { useWriteContract, useWaitForTransactionReceipt } from "wagmi";
import type { Abi, Address } from "viem";

type TxState = "idle" | "pending" | "confirming" | "success" | "error";

interface UseTxFlowReturn {
  state: TxState;
  txHash: `0x${string}` | undefined;
  error: string | null;
  execute: (params: {
    address: Address;
    abi: Abi;
    functionName: string;
    args?: readonly unknown[];
    value?: bigint;
  }) => void;
  reset: () => void;
}

export function useTxFlow(): UseTxFlowReturn {
  const [state, setState] = useState<TxState>("idle");
  const [error, setError] = useState<string | null>(null);

  const { writeContract, data: txHash, reset: resetWrite } = useWriteContract();

  const {
    isSuccess,
    isError,
    error: receiptError,
  } = useWaitForTransactionReceipt({
    hash: txHash,
  });

  useEffect(() => {
    if (isSuccess && state === "confirming") {
      setState("success");
    }
    if (isError && state === "confirming") {
      setState("error");
      setError(receiptError?.message ?? "Transaction failed");
    }
  }, [isSuccess, isError, state, receiptError]);

  const execute: UseTxFlowReturn["execute"] = useCallback(
    (params) => {
      setState("pending");
      setError(null);
      writeContract(params, {
        onSuccess: () => setState("confirming"),
        onError: (err) => {
          setState("error");
          setError(err.message ?? "Transaction rejected");
        },
      });
    },
    [writeContract],
  );

  const reset = useCallback(() => {
    setState("idle");
    setError(null);
    resetWrite();
  }, [resetWrite]);

  return { state, txHash, error, execute, reset };
}
