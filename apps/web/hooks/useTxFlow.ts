"use client";

import { useState, useCallback, useEffect } from "react";
import {
  useWriteContract,
  useWaitForTransactionReceipt,
  useSendTransaction,
  useAccount,
} from "wagmi";
import type { Abi, Address } from "viem";

type TxState = "idle" | "pending" | "confirming" | "success" | "error";

const EXPECTED_CHAIN_ID = parseInt(
  process.env.NEXT_PUBLIC_BASE_CHAIN_ID ?? "84532",
);

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
  executeRaw: (params: {
    to: Address;
    data?: `0x${string}`;
    value?: bigint;
  }) => void;
  reset: () => void;
}

export function useTxFlow(): UseTxFlowReturn {
  const [state, setState] = useState<TxState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [txHash, setTxHash] = useState<`0x${string}` | undefined>(undefined);

  const { chain } = useAccount();
  const { writeContract, reset: resetWrite } = useWriteContract();
  const { sendTransaction, reset: resetSend } = useSendTransaction();

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
      if (chain?.id !== EXPECTED_CHAIN_ID) {
        setState("error");
        setError("Please switch to the Base network");
        return;
      }
      setState("pending");
      setError(null);
      writeContract(params, {
        onSuccess: (hash) => {
          setTxHash(hash);
          setState("confirming");
        },
        onError: (err) => {
          setState("error");
          setError(err.message ?? "Transaction rejected");
        },
      });
    },
    [writeContract, chain],
  );

  const executeRaw = useCallback(
    (params: { to: Address; data?: `0x${string}`; value?: bigint }) => {
      if (chain?.id !== EXPECTED_CHAIN_ID) {
        setState("error");
        setError("Please switch to the Base network");
        return;
      }
      setState("pending");
      setError(null);
      sendTransaction(params, {
        onSuccess: (hash) => {
          setTxHash(hash);
          setState("confirming");
        },
        onError: (err) => {
          setState("error");
          setError(err.message ?? "Transaction rejected");
        },
      });
    },
    [sendTransaction, chain],
  );

  const reset = useCallback(() => {
    setState("idle");
    setError(null);
    setTxHash(undefined);
    resetWrite();
    resetSend();
  }, [resetWrite, resetSend]);

  return { state, txHash, error, execute, executeRaw, reset };
}
