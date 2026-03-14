"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  Plus,
  Clock,
  CheckCircle,
  AlertTriangle,
  DollarSign,
} from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useAuthStore } from "@/lib/stores/auth";
import { isFreelancer } from "@/lib/format";
import { fetchGigs, type GigQueryParams } from "@/lib/api/gigs";
import type { Gig } from "@/types/gig";

type Filter = "all" | "DRAFT" | "OPEN" | "IN_PROGRESS" | "COMPLETED";

const FILTERS: { label: string; value: Filter }[] = [
  { label: "All", value: "all" },
  { label: "Draft", value: "DRAFT" },
  { label: "Open", value: "OPEN" },
  { label: "In Progress", value: "IN_PROGRESS" },
  { label: "Completed", value: "COMPLETED" },
];

function statusIcon(status: string) {
  switch (status) {
    case "DRAFT":
      return <Clock className="h-4 w-4 text-neutral-400" />;
    case "OPEN":
      return <Briefcase className="h-4 w-4 text-blue-500" />;
    case "IN_PROGRESS":
      return <Clock className="h-4 w-4 text-amber-500" />;
    case "COMPLETED":
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case "DISPUTED":
      return <AlertTriangle className="h-4 w-4 text-red-500" />;
    default:
      return <Briefcase className="h-4 w-4 text-neutral-400" />;
  }
}

function GigsContent() {
  const user = useAuthStore((s) => s.user);
  const isFl = user ? isFreelancer(user.role) : false;
  const [gigs, setGigs] = useState<Gig[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("all");

  useEffect(() => {
    setLoading(true);
    const params: GigQueryParams = { page_size: 50 };
    if (filter !== "all") params.status = filter;
    fetchGigs(params)
      .then((res) => {
        // Filter to only gigs where user is client or freelancer
        const mine = (res.gigs ?? []).filter(
          (g) => g.client_id === user?.id || g.freelancer_id === user?.id,
        );
        setGigs(mine);
      })
      .catch(() => setGigs([]))
      .finally(() => setLoading(false));
  }, [filter, user?.id]);

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-neutral-800">My Gigs</h1>
        {!isFl && (
          <Link href="/gigs/new">
            <Button variant="primary">
              <Plus className="mr-1.5 h-4 w-4" />
              Post a Gig
            </Button>
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              filter === f.value
                ? "bg-primary-500 text-white"
                : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <Spinner size="lg" />
        </div>
      ) : gigs.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="No gigs found"
          description={
            isFl
              ? "You haven't been assigned to any gigs yet. Browse open gigs to get started."
              : "You haven't created any gigs yet. Post your first gig to find talent."
          }
          actionLabel={isFl ? "Browse Gigs" : "Post a Gig"}
          actionHref={isFl ? "/gigs" : "/gigs/new"}
        />
      ) : (
        <div className="space-y-3">
          {gigs.map((gig) => {
            const milestonesDone = gig.milestones.filter(
              (m) => m.status === "APPROVED" || m.status === "PAID",
            ).length;
            const totalMilestones = gig.milestones.length;
            const progress =
              totalMilestones > 0
                ? Math.round((milestonesDone / totalMilestones) * 100)
                : 0;

            return (
              <Link key={gig.id} href={`/gigs/${gig.id}`}>
                <Card className="flex items-start gap-4 border border-neutral-200 transition-shadow hover:shadow-md">
                  <div className="mt-1 shrink-0">{statusIcon(gig.status)}</div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="truncate text-sm font-semibold text-neutral-800">
                        {gig.title}
                      </h3>
                      <StatusBadge status={gig.status} />
                    </div>
                    <p className="mt-1 line-clamp-1 text-xs text-neutral-500">
                      {gig.description}
                    </p>
                    <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-neutral-500">
                      <span className="inline-flex items-center gap-1">
                        <DollarSign className="h-3.5 w-3.5" />
                        {gig.total_amount} {gig.currency}
                      </span>
                      {totalMilestones > 0 && (
                        <span>
                          {milestonesDone}/{totalMilestones} milestones
                        </span>
                      )}
                      {totalMilestones > 0 && (
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-20 overflow-hidden rounded-full bg-neutral-200">
                            <div
                              className="h-full rounded-full bg-primary-500 transition-all"
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                          <span>{progress}%</span>
                        </div>
                      )}
                      {gig.skills.length > 0 && (
                        <div className="flex gap-1">
                          {gig.skills.slice(0, 3).map((s) => (
                            <Badge key={s} variant="default">
                              {s}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function MyGigsPage() {
  return (
    <AuthGuard>
      <DashboardLayout>
        <GigsContent />
      </DashboardLayout>
    </AuthGuard>
  );
}
