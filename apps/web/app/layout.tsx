import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers/Providers";
import { NavBar } from "@/components/layout/NavBar";
import { ToastContainer } from "@/components/ui/Toast";
import { NetworkSwitchPrompt } from "@/components/web3/NetworkSwitchPrompt";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "SkillBridge — AI-Powered Freelance Platform",
  description:
    "Hire top freelancers with smart contract escrow and AI-powered code review on Base L2.",
  openGraph: {
    title: "SkillBridge — AI-Powered Freelance Platform",
    description:
      "Hire top freelancers with smart contract escrow and AI-powered code review on Base L2.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-neutral-50 font-sans text-neutral-900 antialiased">
        <Providers>
          <div className="flex min-h-screen flex-col">
            <NavBar />
            <NetworkSwitchPrompt />
            <main className="flex-1">
              <ErrorBoundary>{children}</ErrorBoundary>
            </main>
          </div>
          <ToastContainer />
        </Providers>
      </body>
    </html>
  );
}
