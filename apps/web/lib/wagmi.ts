import { http, createConfig, createStorage, cookieStorage } from "wagmi";
import { base, baseSepolia } from "wagmi/chains";
import { coinbaseWallet, injected, walletConnect } from "wagmi/connectors";

const projectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID ?? "";

const connectors =
  typeof window !== "undefined"
    ? [
        injected(),
        coinbaseWallet({ appName: "SkillBridge" }),
        ...(projectId ? [walletConnect({ projectId })] : []),
      ]
    : [injected(), coinbaseWallet({ appName: "SkillBridge" })];

export const config = createConfig({
  chains: [base, baseSepolia],
  ssr: true,
  storage: createStorage({ storage: cookieStorage }),
  connectors,
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
