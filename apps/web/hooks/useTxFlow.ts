"use client";

import { useState, useCallback } from "react";
import { useWallet, useConnection } from "@solana/wallet-adapter-react";
import { Transaction } from "@solana/web3.js";

type TxState = "idle" | "pending" | "confirming" | "success" | "error";

interface UseTxFlowReturn {
  state: TxState;
  txHash: string | undefined;
  error: string | null;
  /** Send a serialized transaction (base64-encoded) from the API */
  executeSerialized: (serializedTx: string) => Promise<void>;
  /** Send a pre-built Transaction object */
  executeTransaction: (transaction: Transaction) => Promise<void>;
  reset: () => void;
}

export function useTxFlow(): UseTxFlowReturn {
  const [state, setState] = useState<TxState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [txHash, setTxHash] = useState<string | undefined>(undefined);

  const { publicKey, signTransaction } = useWallet();
  const { connection } = useConnection();

  const sendAndConfirm = useCallback(
    async (transaction: Transaction) => {
      if (!publicKey || !signTransaction) {
        setState("error");
        setError("Wallet not connected or does not support signing");
        return;
      }

      setState("pending");
      setError(null);

      try {
        const signed = await signTransaction(transaction);
        const rawTx = signed.serialize();
        const signature = await connection.sendRawTransaction(rawTx);
        setTxHash(signature);
        setState("confirming");

        const latestBlockhash =
          await connection.getLatestBlockhash("confirmed");
        const confirmation = await connection.confirmTransaction(
          { signature, ...latestBlockhash },
          "confirmed",
        );
        if (confirmation.value.err) {
          setState("error");
          setError("Transaction failed on chain");
        } else {
          setState("success");
        }
      } catch (err) {
        setState("error");
        const msg = err instanceof Error ? err.message : "Transaction rejected";
        setError(msg);
      }
    },
    [publicKey, signTransaction, connection],
  );

  const executeSerialized = useCallback(
    async (serializedTx: string) => {
      const bytes = Uint8Array.from(atob(serializedTx), (c) => c.charCodeAt(0));
      const tx = Transaction.from(bytes);
      await sendAndConfirm(tx);
    },
    [sendAndConfirm],
  );

  const executeTransaction = useCallback(
    async (transaction: Transaction) => {
      await sendAndConfirm(transaction);
    },
    [sendAndConfirm],
  );

  const reset = useCallback(() => {
    setState("idle");
    setError(null);
    setTxHash(undefined);
  }, []);

  return { state, txHash, error, executeSerialized, executeTransaction, reset };
}
