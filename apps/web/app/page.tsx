"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  Users,
  Code,
  CheckCircle,
  Shield,
  Bot,
  Award,
  Fingerprint,
  Briefcase,
  DollarSign,
  UserCheck,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import { GigCard } from "@/components/gigs/GigCard";
import { GigCardSkeleton } from "@/components/gigs/GigCardSkeleton";
import { Footer } from "@/components/layout/Footer";
import { fetchGigs } from "@/lib/api/gigs";
import type { Gig } from "@/types/gig";

const steps = [
  {
    icon: FileText,
    title: "Post a Gig",
    description: "Define milestones, acceptance criteria, and fund the escrow.",
  },
  {
    icon: Users,
    title: "Apply & Get Hired",
    description: "Freelancers submit proposals. Clients choose the best fit.",
  },
  {
    icon: Code,
    title: "Submit Work",
    description: "Deliver code, designs, or deliverables for each milestone.",
  },
  {
    icon: CheckCircle,
    title: "AI Reviews & Get Paid",
    description:
      "AI verifies quality. Approved milestones release funds instantly.",
  },
];

const trustBadges = [
  {
    icon: Shield,
    title: "Smart Contract Escrow",
    description: "Funds locked on Solana until milestones are approved.",
  },
  {
    icon: Bot,
    title: "AI Code Review",
    description: "Automated quality verification powered by Claude.",
  },
  {
    icon: Award,
    title: "On-Chain Reputation",
    description: "Portable, verifiable work history on the blockchain.",
  },
  {
    icon: Fingerprint,
    title: "SIWE Auth",
    description: "Sign in with your wallet. No passwords needed.",
  },
];

const stats = [
  { icon: Briefcase, value: "150+", label: "Active Gigs" },
  { icon: DollarSign, value: "$2.4M", label: "Total Paid Out" },
  { icon: UserCheck, value: "1,200+", label: "Freelancers" },
  { icon: Users, value: "500+", label: "Clients" },
];

export default function HomePage() {
  const [featuredGigs, setFeaturedGigs] = useState<Gig[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGigs({ page_size: 6, sort: "created_at", status: "OPEN" })
      .then((res) => setFeaturedGigs(res.gigs))
      .catch(() => setFeaturedGigs([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      {/* Hero */}
      <section className="bg-white">
        <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6 md:py-24">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-bold tracking-tight text-neutral-900 md:text-5xl lg:text-6xl">
              The freelance marketplace with{" "}
              <span className="text-primary-600">AI-verified work</span> and{" "}
              <span className="text-web3-500">on-chain escrow</span>
            </h1>
            <p className="mt-6 text-lg text-neutral-500 md:text-xl">
              Hire top talent with confidence. Smart contracts guarantee
              payment. AI verifies deliverable quality. No middlemen, no
              disputes.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link href="/gigs">
                <Button size="lg">
                  Find Talent
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/auth">
                <Button variant="outline" size="lg">
                  Start Earning
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="bg-neutral-50">
        <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6 md:py-20">
          <h2 className="text-center text-2xl font-bold text-neutral-800 md:text-3xl">
            How It Works
          </h2>
          <p className="mt-2 text-center text-neutral-500">
            From posting a gig to getting paid — in four simple steps.
          </p>

          <div className="mt-12 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map((step, i) => (
              <div key={step.title} className="relative text-center">
                {i < steps.length - 1 && (
                  <div className="absolute right-0 top-8 hidden h-0.5 w-full translate-x-1/2 bg-neutral-200 lg:block" />
                )}
                <div className="relative mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary-50 text-primary-600">
                  <step.icon className="h-7 w-7" />
                  <span className="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full bg-primary-600 text-xs font-bold text-white">
                    {i + 1}
                  </span>
                </div>
                <h3 className="mt-4 text-lg font-semibold text-neutral-800">
                  {step.title}
                </h3>
                <p className="mt-1 text-sm text-neutral-500">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust Badges */}
      <section className="bg-white">
        <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6 md:py-20">
          <h2 className="text-center text-2xl font-bold text-neutral-800 md:text-3xl">
            Built on Trust
          </h2>
          <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {trustBadges.map((badge) => (
              <div
                key={badge.title}
                className="rounded-lg border border-neutral-200 bg-white p-6 text-center shadow-sm"
              >
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary-50 text-primary-600">
                  <badge.icon className="h-6 w-6" />
                </div>
                <h3 className="mt-4 text-base font-semibold text-neutral-800">
                  {badge.title}
                </h3>
                <p className="mt-1 text-sm text-neutral-500">
                  {badge.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Gigs */}
      <section className="bg-neutral-50">
        <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6 md:py-20">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-neutral-800 md:text-3xl">
              Featured Gigs
            </h2>
            <Link href="/gigs">
              <Button variant="ghost" size="sm">
                View All
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>

          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {loading
              ? Array.from({ length: 6 }).map((_, i) => (
                  <GigCardSkeleton key={i} />
                ))
              : featuredGigs.map((gig) => <GigCard key={gig.id} gig={gig} />)}
          </div>

          {!loading && featuredGigs.length === 0 && (
            <p className="mt-8 text-center text-neutral-500">
              No gigs yet. Be the first to{" "}
              <Link
                href="/gigs/new"
                className="text-primary-600 hover:underline"
              >
                post a gig
              </Link>
              .
            </p>
          )}
        </div>
      </section>

      {/* Stats */}
      <section className="bg-white">
        <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6 md:py-20">
          <div className="grid grid-cols-2 gap-6 lg:grid-cols-4">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary-50 text-primary-600">
                  <stat.icon className="h-6 w-6" />
                </div>
                <p className="mt-3 text-3xl font-bold text-neutral-900">
                  {stat.value}
                </p>
                <p className="mt-1 text-sm text-neutral-500">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-primary-600">
        <div className="mx-auto max-w-[1280px] px-4 py-16 text-center md:px-6 md:py-20">
          <h2 className="text-2xl font-bold text-white md:text-3xl">
            Ready to get started?
          </h2>
          <p className="mt-3 text-primary-100">
            Connect your wallet and join the future of freelancing.
          </p>
          <div className="mt-8 flex justify-center">
            <Link href="/auth">
              <Button
                variant="outline"
                size="lg"
                className="border-white text-white hover:bg-white hover:text-primary-600"
              >
                Let&apos;s Go
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}
