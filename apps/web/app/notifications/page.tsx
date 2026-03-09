"use client";

import { useEffect, useState, useCallback } from "react";
import { Bell, Check, Filter } from "lucide-react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";
import { Badge } from "@/components/ui/Badge";
import {
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from "@/lib/api/notifications";
import { notificationIcon, notificationLabel } from "@/lib/notificationHelpers";
import type { Notification, NotificationType } from "@/types/notification";
import { cn } from "@/lib/utils";

const filterOptions: { label: string; value: string }[] = [
  { label: "All", value: "all" },
  { label: "Unread", value: "unread" },
  { label: "Proposals", value: "PROPOSAL_RECEIVED" },
  { label: "Reviews", value: "REVIEW_COMPLETE" },
  { label: "Milestones", value: "MILESTONE_APPROVED" },
  { label: "Disputes", value: "DISPUTE_FILED" },
];

function NotificationsContent() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filter, setFilter] = useState("all");

  const load = useCallback(() => {
    setLoading(true);
    const params: {
      page: number;
      limit: number;
      unread?: boolean;
      type?: string;
    } = {
      page,
      limit: 20,
    };
    if (filter === "unread") params.unread = true;
    else if (filter !== "all") params.type = filter;

    getNotifications(params)
      .then((res) => {
        setNotifications(res.notifications);
        setTotalPages(res.total_pages);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page, filter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleClick = async (n: Notification) => {
    if (!n.read) {
      await markNotificationRead(n.id).catch(() => {});
    }
    if (n.link) window.location.href = n.link;
    else load();
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead().catch(() => {});
    load();
  };

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold text-neutral-800">Notifications</h1>
        <Button variant="outline" size="sm" onClick={handleMarkAllRead}>
          <Check className="mr-1.5 h-4 w-4" />
          Mark all read
        </Button>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap gap-2">
        {filterOptions.map((opt) => (
          <button
            key={opt.value}
            onClick={() => {
              setFilter(opt.value);
              setPage(1);
            }}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              filter === opt.value
                ? "border-primary-200 bg-primary-50 text-primary-700"
                : "border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50",
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <Spinner size="lg" />
        </div>
      ) : notifications.length === 0 ? (
        <EmptyState
          icon={Bell}
          title="No notifications"
          description="You're all caught up!"
        />
      ) : (
        <div className="space-y-2">
          {notifications.map((n) => {
            const Icon = notificationIcon(n.type);
            return (
              <button
                key={n.id}
                onClick={() => handleClick(n)}
                className={cn(
                  "flex w-full items-start gap-4 rounded-lg border p-4 text-left transition-colors hover:bg-neutral-50",
                  n.read
                    ? "border-neutral-200 bg-white"
                    : "border-primary-200 bg-primary-50/50",
                )}
              >
                <div
                  className={cn(
                    "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                    n.read ? "bg-neutral-100" : "bg-primary-100",
                  )}
                >
                  <Icon
                    className={cn(
                      "h-4 w-4",
                      n.read ? "text-neutral-400" : "text-primary-600",
                    )}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge variant={n.read ? "default" : "primary"}>
                      {notificationLabel(n.type)}
                    </Badge>
                    {!n.read && (
                      <span className="h-2 w-2 rounded-full bg-primary-500" />
                    )}
                  </div>
                  <p className="mt-1 text-sm text-neutral-700">{n.message}</p>
                  <p className="mt-1 text-xs text-neutral-400">
                    {new Date(n.created_at).toLocaleString()}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      )}

      <Pagination
        currentPage={page}
        totalPages={totalPages}
        onPageChange={setPage}
        className="mt-6 justify-center"
      />
    </div>
  );
}

export default function NotificationsPage() {
  return (
    <AuthGuard>
      <DashboardLayout>
        <NotificationsContent />
      </DashboardLayout>
    </AuthGuard>
  );
}
