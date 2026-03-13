"use client";

import { useState } from "react";
import {
  Shield,
  Bot,
  ChevronDown,
  FileText,
  CheckCircle,
  DollarSign,
  Lock,
  ArrowRight,
  Code,
  Eye,
  MessageSquare,
  Github,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Footer } from "@/components/layout/Footer";
import { cn } from "@/lib/utils";

const faqItems = [
  {
    question: "How does the escrow work?",
    answer:
      "When a client creates a gig, they deposit the total budget into a smart contract on Base L2. Funds are locked and only released when milestones are approved — either by the client or through AI review verification. Neither party can withdraw funds unilaterally.",
  },
  {
    question: "What happens if there's a dispute?",
    answer:
      "Disputes trigger a 3-day discussion period between client and freelancer. If unresolved, the case goes to community arbitration where evidence (including AI review reports) is evaluated. The resolution determines how locked funds are split.",
  },
  {
    question: "How does AI code review work?",
    answer:
      "When a freelancer submits work, they can trigger an AI review by mentioning @openreview on their PR. The AI (Claude) analyzes the code against the milestone's acceptance criteria, runs quality checks, and delivers a PASS/FAIL verdict with detailed findings.",
  },
  {
    question: "What are the platform fees?",
    answer:
      "SkillBridge charges a 5% platform fee on each milestone payment, deducted automatically when funds are released. There are no fees for creating accounts, browsing gigs, or submitting proposals.",
  },
  {
    question: "Which wallets are supported?",
    answer:
      "We support Phantom, Solflare, Backpack, and other Solana-compatible wallets. You can also sign up with email if you prefer traditional authentication — you'll need a wallet only when receiving or sending funds.",
  },
  {
    question: "What blockchain does SkillBridge use?",
    answer:
      "SkillBridge runs on Solana, a high-performance blockchain with sub-second finality and transaction fees under $0.01, making micro-payments for milestones practical.",
  },
];

const fees = [
  { item: "Account creation", fee: "Free" },
  { item: "Browsing & applying", fee: "Free" },
  { item: "Posting a gig", fee: "Free" },
  { item: "Platform fee (per milestone)", fee: "5%" },
  { item: "Escrow deposit gas", fee: "~$0.01 (Base L2)" },
  { item: "Fund release gas", fee: "~$0.01 (Base L2)" },
];

function FAQItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-neutral-200">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between py-4 text-left min-h-[44px]"
      >
        <span className="text-base font-medium text-neutral-800">
          {question}
        </span>
        <ChevronDown
          className={cn(
            "h-5 w-5 shrink-0 text-neutral-400 transition-transform",
            open && "rotate-180",
          )}
        />
      </button>
      {open && (
        <p className="pb-4 text-sm leading-relaxed text-neutral-500">
          {answer}
        </p>
      )}
    </div>
  );
}

export default function AboutPage() {
  return (
    <>
      {/* Hero */}
      <section className="bg-white">
        <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6 md:py-20">
          <div className="mx-auto max-w-2xl text-center">
            <h1 className="text-3xl font-bold text-neutral-900 md:text-4xl">
              About SkillBridge
            </h1>
            <p className="mt-4 text-lg text-neutral-500">
              The freelance marketplace where trust is enforced by technology,
              not intermediaries. Smart contracts guarantee payment. AI verifies
              work quality.
            </p>
          </div>
        </div>
      </section>

      {/* How Escrow Works */}
      <section className="bg-neutral-50">
        <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6 md:py-20">
          <h2 className="text-center text-2xl font-bold text-neutral-800 md:text-3xl">
            How the Escrow Works
          </h2>
          <p className="mt-2 text-center text-neutral-500">
            Funds are protected at every step of the process.
          </p>

          <div className="mx-auto mt-12 max-w-3xl">
            <div className="relative">
              {/* Vertical line */}
              <div className="absolute left-6 top-0 h-full w-0.5 bg-neutral-200 md:left-8" />

              {[
                {
                  icon: FileText,
                  title: "Client Creates Gig",
                  desc: "Defines milestones, acceptance criteria, and total budget.",
                },
                {
                  icon: Lock,
                  title: "Funds Deposited to Escrow",
                  desc: "Client sends total budget to a smart contract on Base L2. Funds are locked — neither party can withdraw.",
                },
                {
                  icon: Code,
                  title: "Freelancer Submits Work",
                  desc: "Deliverables submitted for each milestone: code repos, files, or links.",
                },
                {
                  icon: Eye,
                  title: "AI Reviews Quality",
                  desc: "Claude analyzes submission against acceptance criteria and delivers a PASS/FAIL verdict.",
                },
                {
                  icon: CheckCircle,
                  title: "Milestone Approved",
                  desc: "Client approves (or AI verdict auto-approves). Smart contract releases milestone funds.",
                },
                {
                  icon: DollarSign,
                  title: "Funds Released",
                  desc: "Freelancer receives payment minus 5% platform fee. Instant, on-chain, verifiable.",
                },
              ].map((step, i) => (
                <div key={i} className="relative flex gap-4 pb-8 md:gap-6">
                  <div className="relative z-10 flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary-50 text-primary-600 md:h-16 md:w-16">
                    <step.icon className="h-5 w-5 md:h-6 md:w-6" />
                  </div>
                  <div className="pt-2 md:pt-4">
                    <h3 className="text-base font-semibold text-neutral-800">
                      {step.title}
                    </h3>
                    <p className="mt-1 text-sm text-neutral-500">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* How AI Review Works */}
      <section className="bg-white">
        <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6 md:py-20">
          <h2 className="text-center text-2xl font-bold text-neutral-800 md:text-3xl">
            How AI Review Works
          </h2>
          <p className="mt-2 text-center text-neutral-500">
            Objective quality verification powered by Claude.
          </p>

          <div className="mx-auto mt-12 grid max-w-4xl grid-cols-1 gap-6 md:grid-cols-3">
            {[
              {
                icon: MessageSquare,
                title: "1. Trigger Review",
                desc: "Freelancer mentions @openreview on their pull request to start AI analysis.",
              },
              {
                icon: Bot,
                title: "2. AI Analyzes",
                desc: "Claude reviews code against acceptance criteria: correctness, quality, security, and completeness.",
              },
              {
                icon: Shield,
                title: "3. Verdict Delivered",
                desc: "PASS or FAIL with detailed findings. A passing verdict can auto-release milestone funds.",
              },
            ].map((step) => (
              <Card key={step.title} variant="bordered" className="text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-web3-50 text-web3-500">
                  <step.icon className="h-6 w-6" />
                </div>
                <h3 className="mt-4 text-base font-semibold text-neutral-800">
                  {step.title}
                </h3>
                <p className="mt-2 text-sm text-neutral-500">{step.desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Fee Structure */}
      <section id="fees" className="bg-neutral-50">
        <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6 md:py-20">
          <h2 className="text-center text-2xl font-bold text-neutral-800 md:text-3xl">
            Fee Structure
          </h2>
          <p className="mt-2 text-center text-neutral-500">
            Transparent, simple pricing. No hidden costs.
          </p>

          <div className="mx-auto mt-10 max-w-lg">
            <Card>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200 text-left">
                    <th className="pb-3 font-medium text-neutral-500">Item</th>
                    <th className="pb-3 text-right font-medium text-neutral-500">
                      Fee
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {fees.map((row) => (
                    <tr key={row.item}>
                      <td className="py-3 text-neutral-700">{row.item}</td>
                      <td className="py-3 text-right font-medium text-neutral-800">
                        {row.fee}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="bg-white">
        <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6 md:py-20">
          <h2 className="text-center text-2xl font-bold text-neutral-800 md:text-3xl">
            Frequently Asked Questions
          </h2>

          <div className="mx-auto mt-10 max-w-2xl">
            {faqItems.map((item) => (
              <FAQItem key={item.question} {...item} />
            ))}
          </div>
        </div>
      </section>

      {/* Open Source CTA */}
      <section className="bg-neutral-50">
        <div className="mx-auto max-w-[1280px] px-4 py-16 text-center md:px-6 md:py-20">
          <Github className="mx-auto h-10 w-10 text-neutral-800" />
          <h2 className="mt-4 text-2xl font-bold text-neutral-800">
            Open Source
          </h2>
          <p className="mt-2 text-neutral-500">
            SkillBridge is open source. Contribute, audit, or fork the codebase.
          </p>
          <div className="mt-6">
            <a
              href="https://github.com/agarwalvivek29/skillbridge"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline" size="lg">
                View on GitHub
                <ArrowRight className="h-4 w-4" />
              </Button>
            </a>
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}
