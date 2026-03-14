"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  Clock,
  DollarSign,
  Users,
  ArrowRight,
  Shield,
  Star,
  FileText,
  TrendingUp,
} from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Badge } from "@/components/ui/Badge";
import { useAuthStore } from "@/lib/stores/auth";
import { isFreelancer, formatAmount } from "@/lib/format";
import {
  getClientDashboard,
  getFreelancerDashboard,
  type ClientDashboard,
  type FreelancerDashboard,
} from "@/lib/api/dashboard";

/* ---------- Client Dashboard ---------- */

function ClientDashboardView() {
  const [data, setData] = useState<ClientDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getClientDashboard()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-neutral-800">
          Client Dashboard
        </h1>
        <Link href="/gigs/new">
          <Button variant="primary">Post a Gig</Button>
        </Link>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Card className="text-center">
          <Briefcase className="mx-auto h-5 w-5 text-neutral-400" />
          <div className="mt-2 text-2xl font-bold text-neutral-800">
            {data.stats.total_gigs}
          </div>
          <div className="text-xs text-neutral-500">Total Gigs</div>
        </Card>
        <Card className="text-center">
          <Users className="mx-auto h-5 w-5 text-neutral-400" />
          <div className="mt-2 text-2xl font-bold text-neutral-800">
            {data.stats.active_freelancers}
          </div>
          <div className="text-xs text-neutral-500">Active Freelancers</div>
        </Card>
        <Card className="text-center">
          <Clock className="mx-auto h-5 w-5 text-neutral-400" />
          <div className="mt-2 text-2xl font-bold text-neutral-800">
            {data.stats.avg_approval_time}
          </div>
          <div className="text-xs text-neutral-500">Avg Approval Time</div>
        </Card>
      </div>

      {/* Active gigs */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-neutral-800">
          Active Gigs
        </h2>
        {data.active_gigs.length === 0 ? (
          <Card>
            <p className="py-4 text-center text-sm text-neutral-500">
              No active gigs.{" "}
              <Link
                href="/gigs/new"
                className="text-primary-600 hover:text-primary-700"
              >
                Post your first gig
              </Link>
            </p>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {data.active_gigs.map((gig) => (
              <Link key={gig.id} href={`/gigs/${gig.id}/manage`}>
                <Card className="transition-shadow hover:shadow-lg">
                  <h3 className="text-sm font-semibold text-neutral-800">
                    {gig.title}
                  </h3>
                  <div className="mt-2 flex items-center gap-3">
                    <StatusBadge status={gig.status} />
                    <span className="text-xs text-neutral-500">
                      {gig.milestones.length} milestones
                    </span>
                  </div>
                  {/* Progress bar */}
                  <div className="mt-3">
                    <div className="h-2 w-full rounded-full bg-neutral-200">
                      <div
                        className="h-2 rounded-full bg-primary-500 transition-all"
                        style={{
                          width: `${
                            gig.milestones.length > 0
                              ? (gig.milestones.filter(
                                  (m) =>
                                    m.status === "PAID" ||
                                    m.status === "APPROVED",
                                ).length /
                                  gig.milestones.length) *
                                100
                              : 0
                          }%`,
                        }}
                      />
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-xs text-neutral-500">
                    <span>{gig.proposal_count} proposals</span>
                    <span className="font-medium text-neutral-700">
                      {formatAmount(gig.escrow_balance)} SOL locked
                    </span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Pending actions */}
      {data.pending_actions.length > 0 && (
        <section>
          <h2 className="mb-4 text-lg font-semibold text-neutral-800">
            Pending Actions
          </h2>
          <div className="space-y-2">
            {data.pending_actions.map((action, i) => (
              <Link key={i} href={action.link}>
                <Card className="flex items-center justify-between transition-colors hover:bg-neutral-50">
                  <div>
                    <p className="text-sm font-medium text-neutral-800">
                      {action.label}
                    </p>
                    <p className="text-xs text-neutral-500">
                      {action.gig_title}
                    </p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-neutral-400" />
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Escrow overview */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-neutral-800">
          Escrow Overview
        </h2>
        <Card>
          <div className="mb-4 text-center">
            <DollarSign className="mx-auto h-6 w-6 text-web3-500" />
            <div className="mt-1 text-2xl font-bold text-neutral-800">
              {formatAmount(data.escrow_overview.total_locked)} SOL
            </div>
            <div className="text-xs text-neutral-500">Total Locked</div>
          </div>
          {data.escrow_overview.per_gig.length > 0 && (
            <div className="space-y-2 border-t border-neutral-200 pt-4">
              {data.escrow_overview.per_gig.map((g) => (
                <div
                  key={g.gig_id}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-neutral-600">{g.title}</span>
                  <span className="font-medium text-neutral-800">
                    {formatAmount(g.amount)} SOL
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </section>

      {/* Recent activity */}
      {data.recent_activity.length > 0 && (
        <section>
          <h2 className="mb-4 text-lg font-semibold text-neutral-800">
            Recent Activity
          </h2>
          <Card>
            <div className="space-y-3">
              {data.recent_activity.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-3 border-b border-neutral-100 pb-3 last:border-0 last:pb-0"
                >
                  <div className="mt-0.5 h-2 w-2 rounded-full bg-primary-400" />
                  <div className="flex-1">
                    <p className="text-sm text-neutral-700">{event.message}</p>
                    <p className="text-xs text-neutral-400">
                      {new Date(event.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </section>
      )}
    </div>
  );
}

/* ---------- Freelancer Dashboard ---------- */

function FreelancerDashboardView() {
  const [data, setData] = useState<FreelancerDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getFreelancerDashboard()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-neutral-800">
        Freelancer Dashboard
      </h1>

      {/* Earnings summary */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Card className="text-center">
          <DollarSign className="mx-auto h-5 w-5 text-success-500" />
          <div className="mt-2 text-2xl font-bold text-neutral-800">
            {formatAmount(data.earnings.total_earned)} SOL
          </div>
          <div className="text-xs text-neutral-500">Total Earned</div>
        </Card>
        <Card className="text-center">
          <Clock className="mx-auto h-5 w-5 text-web3-500" />
          <div className="mt-2 text-2xl font-bold text-neutral-800">
            {formatAmount(data.earnings.pending_payment)} SOL
          </div>
          <div className="text-xs text-neutral-500">Pending Payment</div>
        </Card>
        <Card className="text-center">
          <Shield className="mx-auto h-5 w-5 text-primary-500" />
          <div className="mt-2 text-2xl font-bold text-neutral-800">
            {data.reputation.score}
          </div>
          <div className="text-xs text-neutral-500">
            {data.reputation.badge_tier}
          </div>
        </Card>
      </div>

      {/* Earnings chart placeholder */}
      {data.earnings.last_30_days.length > 0 && (
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-neutral-800">
              Last 30 Days Earnings
            </h2>
          </CardHeader>
          <div className="mt-4 flex h-32 items-end gap-1">
            {data.earnings.last_30_days.map((day, i) => {
              const max = Math.max(
                ...data.earnings.last_30_days.map(
                  (d) => parseFloat(d.amount) || 0,
                ),
                1,
              );
              const height = ((parseFloat(day.amount) || 0) / max) * 100;
              return (
                <div
                  key={i}
                  className="flex-1 rounded-t bg-primary-400 transition-all hover:bg-primary-500"
                  style={{ height: `${Math.max(height, 2)}%` }}
                  title={`${day.date}: ${formatAmount(day.amount)} SOL`}
                />
              );
            })}
          </div>
        </Card>
      )}

      {/* Active milestones */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-neutral-800">
          Active Work
        </h2>
        {data.active_milestones.length === 0 ? (
          <Card>
            <p className="py-4 text-center text-sm text-neutral-500">
              No active milestones.{" "}
              <Link
                href="/gigs"
                className="text-primary-600 hover:text-primary-700"
              >
                Browse gigs
              </Link>
            </p>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {data.active_milestones.map((m) => (
              <Link key={m.id} href={`/gigs/${m.gig_id}/workspace`}>
                <Card className="transition-shadow hover:shadow-lg">
                  <h3 className="text-sm font-semibold text-neutral-800">
                    {m.milestone_name}
                  </h3>
                  <p className="mt-1 text-xs text-neutral-500">{m.gig_title}</p>
                  <div className="mt-3 flex items-center justify-between">
                    <StatusBadge status={m.status} />
                    <span className="text-sm font-medium text-neutral-700">
                      {formatAmount(m.budget)} SOL
                    </span>
                  </div>
                  {m.deadline && (
                    <p className="mt-2 text-xs text-neutral-400">
                      Due: {new Date(m.deadline).toLocaleDateString()}
                    </p>
                  )}
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Applications */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-neutral-800">
          Applications
        </h2>
        {data.applications.length === 0 ? (
          <Card>
            <p className="py-4 text-center text-sm text-neutral-500">
              No pending applications
            </p>
          </Card>
        ) : (
          <div className="space-y-2">
            {data.applications.map((app) => (
              <Link key={app.id} href={`/gigs/${app.gig_id}`}>
                <Card className="flex items-center justify-between transition-colors hover:bg-neutral-50">
                  <div>
                    <p className="text-sm font-medium text-neutral-800">
                      {app.gig_title}
                    </p>
                    <p className="text-xs text-neutral-400">
                      Applied {new Date(app.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <StatusBadge status={app.status} />
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Reputation & Reviews */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-neutral-800">
          Reputation & Reviews
        </h2>
        <Card>
          <div className="mb-4 flex items-center gap-4">
            <div className="text-3xl font-bold text-neutral-800">
              {data.reputation.score}
            </div>
            <Badge variant="web3">{data.reputation.badge_tier}</Badge>
          </div>
          {data.reputation.recent_reviews.length > 0 ? (
            <div className="space-y-3 border-t border-neutral-200 pt-4">
              {data.reputation.recent_reviews.map((r, i) => (
                <div key={i} className="flex items-start gap-2">
                  <div className="flex items-center gap-0.5">
                    {Array.from({ length: 5 }).map((_, j) => (
                      <Star
                        key={j}
                        className={`h-3.5 w-3.5 ${
                          j < r.score
                            ? "fill-secondary-400 text-secondary-400"
                            : "text-neutral-300"
                        }`}
                      />
                    ))}
                  </div>
                  {r.review && (
                    <p className="flex-1 text-sm text-neutral-600">
                      {r.review}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-neutral-500">No reviews yet</p>
          )}
        </Card>
      </section>

      {/* AI Reviews */}
      {data.ai_reviews.length > 0 && (
        <section>
          <h2 className="mb-4 text-lg font-semibold text-neutral-800">
            Recent AI Reviews
          </h2>
          <div className="space-y-2">
            {data.ai_reviews.map((review, i) => (
              <Card key={i} className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-neutral-800">
                    {review.milestone_name}
                  </p>
                  <p className="text-xs text-neutral-400">
                    {new Date(review.created_at).toLocaleDateString()}
                  </p>
                </div>
                <Badge
                  variant={review.verdict === "PASS" ? "success" : "error"}
                >
                  {review.verdict}
                </Badge>
              </Card>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

/* ---------- Route Handler ---------- */

function DashboardContent() {
  const user = useAuthStore((s) => s.user);

  if (!user) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return isFreelancer(user.role) ? (
    <FreelancerDashboardView />
  ) : (
    <ClientDashboardView />
  );
}

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardLayout>
        <DashboardContent />
      </DashboardLayout>
    </AuthGuard>
  );
}
