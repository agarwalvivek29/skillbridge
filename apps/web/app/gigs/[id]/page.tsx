"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Calendar, ArrowLeft, ExternalLink, DollarSign } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Badge } from "@/components/ui/Badge";
import { Avatar } from "@/components/ui/Avatar";
import { Spinner } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { GigCard } from "@/components/gigs/GigCard";
import { GigCardSkeleton } from "@/components/gigs/GigCardSkeleton";
import { Footer } from "@/components/layout/Footer";
import { fetchGig, fetchGigs } from "@/lib/api/gigs";
import { useAuthStore } from "@/lib/stores/auth";
import type { Gig } from "@/types/gig";

export default function GigDetailPage() {
  const params = useParams();
  const router = useRouter();
  const gigId = params.id as string;
  const token = useAuthStore((s) => s.token);

  const [gig, setGig] = useState<Gig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [similarGigs, setSimilarGigs] = useState<Gig[]>([]);
  const [similarLoading, setSimilarLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchGig(gigId);
        if (controller.signal.aborted) return;
        setGig(data);
        setSimilarLoading(true);
        try {
          const res = await fetchGigs({
            page_size: 3,
            category: data.category ?? undefined,
            status: "OPEN",
          });
          if (controller.signal.aborted) return;
          setSimilarGigs(res.gigs.filter((g) => g.id !== gigId).slice(0, 3));
        } catch {
          if (!controller.signal.aborted) setSimilarGigs([]);
        } finally {
          if (!controller.signal.aborted) setSimilarLoading(false);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Failed to load gig");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    load();
    return () => controller.abort();
  }, [gigId]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !gig) {
    return (
      <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6">
        <ErrorState
          icon={ExternalLink}
          title="Gig not found"
          description={error ?? "The gig you're looking for doesn't exist."}
          actionLabel="Browse Gigs"
          onAction={() => router.push("/gigs")}
        />
      </div>
    );
  }

  const postedDate = new Date(gig.created_at).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  const totalMilestoneBudget = gig.milestones.reduce(
    (sum, m) => sum + parseFloat(m.amount || "0"),
    0,
  );

  const handleApply = () => {
    if (!token) {
      router.push("/auth");
    } else {
      router.push(`/gigs/${gigId}/apply`);
    }
  };

  return (
    <>
      <div className="mx-auto max-w-[1280px] px-4 py-8 md:px-6 md:py-12">
        {/* Back link */}
        <Link
          href="/gigs"
          className="mb-6 inline-flex items-center gap-1 text-sm text-neutral-500 transition-colors hover:text-neutral-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Gigs
        </Link>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Header */}
            <div>
              <div className="flex flex-wrap items-start gap-3">
                <h1 className="text-2xl font-bold text-neutral-800 md:text-3xl">
                  {gig.title}
                </h1>
                <StatusBadge status={gig.status} />
              </div>

              <div className="mt-3 flex items-center gap-3">
                <Avatar
                  src={gig.client_avatar_url}
                  name={gig.client_name}
                  walletAddress={gig.client_wallet_address}
                  size="sm"
                />
                <div>
                  <p className="text-sm font-medium text-neutral-700">
                    {gig.client_name ?? "Anonymous Client"}
                  </p>
                  <p className="flex items-center gap-1 text-xs text-neutral-400">
                    <Calendar className="h-3 w-3" />
                    Posted {postedDate}
                  </p>
                </div>
              </div>
            </div>

            {/* Description */}
            <Card>
              <h2 className="text-lg font-semibold text-neutral-800">
                Description
              </h2>
              <div className="mt-3 prose prose-sm prose-neutral max-w-none whitespace-pre-wrap text-neutral-600">
                {gig.description}
              </div>
            </Card>

            {/* Skills */}
            {gig.skills.length > 0 && (
              <Card>
                <h2 className="text-lg font-semibold text-neutral-800">
                  Skills Required
                </h2>
                <div className="mt-3 flex flex-wrap gap-2">
                  {gig.skills.map((skill) => (
                    <Badge key={skill} variant="primary">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </Card>
            )}

            {/* Milestones */}
            {gig.milestones.length > 0 && (
              <Card>
                <h2 className="text-lg font-semibold text-neutral-800">
                  Milestones
                </h2>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-neutral-200 text-left">
                        <th className="pb-3 font-medium text-neutral-500">#</th>
                        <th className="pb-3 font-medium text-neutral-500">
                          Milestone
                        </th>
                        <th className="pb-3 font-medium text-neutral-500">
                          Budget
                        </th>
                        <th className="pb-3 font-medium text-neutral-500">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-100">
                      {gig.milestones.map((m, i) => (
                        <tr key={m.id}>
                          <td className="py-3 text-neutral-400">{i + 1}</td>
                          <td className="py-3">
                            <p className="font-medium text-neutral-700">
                              {m.title}
                            </p>
                            {m.description && (
                              <p className="mt-0.5 text-xs text-neutral-400">
                                {m.description}
                              </p>
                            )}
                          </td>
                          <td className="py-3 text-neutral-600">
                            {m.amount} {m.currency}
                          </td>
                          <td className="py-3">
                            <StatusBadge status={m.status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Budget Breakdown */}
            <Card>
              <h3 className="text-lg font-semibold text-neutral-800">Budget</h3>
              <div className="mt-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-neutral-500">Total Budget</span>
                  <span className="flex items-center gap-1 text-lg font-bold text-neutral-900">
                    <DollarSign className="h-4 w-4" />
                    {gig.total_amount} {gig.currency}
                  </span>
                </div>
                {gig.milestones.length > 0 && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-neutral-500">Across milestones</span>
                    <span className="text-neutral-600">
                      {totalMilestoneBudget} {gig.currency}
                    </span>
                  </div>
                )}
                {gig.deadline && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-neutral-500">Deadline</span>
                    <span className="text-neutral-600">
                      {new Date(gig.deadline).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>

              {gig.status === "OPEN" && (
                <Button onClick={handleApply} size="lg" className="mt-6 w-full">
                  Submit Proposal
                </Button>
              )}
            </Card>

            {/* Gig Meta */}
            <Card>
              <h3 className="text-sm font-medium text-neutral-500">Details</h3>
              <dl className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-neutral-500">Category</dt>
                  <dd className="text-neutral-700">
                    {gig.category ?? "General"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-neutral-500">Milestones</dt>
                  <dd className="text-neutral-700">{gig.milestones.length}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-neutral-500">Status</dt>
                  <dd>
                    <StatusBadge status={gig.status} />
                  </dd>
                </div>
              </dl>
            </Card>
          </div>
        </div>

        {/* Similar Gigs */}
        <section className="mt-16">
          <h2 className="text-xl font-bold text-neutral-800">Similar Gigs</h2>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {similarLoading
              ? Array.from({ length: 3 }).map((_, i) => (
                  <GigCardSkeleton key={i} />
                ))
              : similarGigs.length > 0
                ? similarGigs.map((g) => <GigCard key={g.id} gig={g} />)
                : null}
          </div>
          {!similarLoading && similarGigs.length === 0 && (
            <p className="mt-4 text-sm text-neutral-400">
              No similar gigs found.
            </p>
          )}
        </section>
      </div>

      <Footer />
    </>
  );
}
