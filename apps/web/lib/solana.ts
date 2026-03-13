import { clusterApiUrl } from "@solana/web3.js";

export type SolanaCluster = "mainnet-beta" | "devnet" | "testnet" | "localnet";

export function getSolanaEndpoint(): string {
  return process.env.NEXT_PUBLIC_SOLANA_RPC_URL || clusterApiUrl("devnet");
}

export function getSolanaCluster(): SolanaCluster {
  return (process.env.NEXT_PUBLIC_SOLANA_CLUSTER as SolanaCluster) || "devnet";
}

export function getExplorerUrl(type: "tx" | "address", value: string): string {
  const cluster = getSolanaCluster();
  const clusterParam = cluster === "mainnet-beta" ? "" : `?cluster=${cluster}`;
  return `https://explorer.solana.com/${type}/${value}${clusterParam}`;
}
