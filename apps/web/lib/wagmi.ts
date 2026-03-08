import { http, createConfig } from "wagmi";
import { base, baseSepolia } from "wagmi/chains";
import { coinbaseWallet, injected, walletConnect } from "wagmi/connectors";

const projectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID ?? "";

export const config = createConfig({
  chains: [base, baseSepolia],
  ssr: true,
  connectors: [
    injected(),
    coinbaseWallet({ appName: "SkillBridge" }),
    ...(projectId ? [walletConnect({ projectId })] : []),
  ],
  transports: {
    [base.id]: http(),
    [baseSepolia.id]: http(),
  },
});

declare module "wagmi" {
  interface Register {
    config: typeof config;
  }
}
