"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import { Bell, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/stores/auth";
import {
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from "@/lib/api/notifications";
import type { Notification } from "@/types/notification";
import { notificationIcon, notificationLabel } from "@/lib/notificationHelpers";

export function NotificationBell() {
  const token = useAuthStore((s) => s.token);
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  const load = useCallback(() => {
    if (!token) return;
    getNotifications({ limit: 10, unread: true })
      .then((res) => {
        setNotifications(res.notifications);
        setUnreadCount(res.total);
      })
      .catch(() => {});
  }, [token]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleMarkRead = async (id: string) => {
    await markNotificationRead(id).catch(() => {});
    load();
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead().catch(() => {});
    load();
  };

  if (!token) return null;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative rounded-md p-2 text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-error-500 text-[10px] font-medium text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 rounded-lg border border-neutral-200 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
            <h3 className="text-sm font-semibold text-neutral-800">
              Notifications
            </h3>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700"
              >
                <Check className="h-3 w-3" />
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-[400px] overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-neutral-500">
                No new notifications
              </p>
            ) : (
              notifications.map((n) => {
                const Icon = notificationIcon(n.type);
                return (
                  <button
                    key={n.id}
                    onClick={() => {
                      handleMarkRead(n.id);
                      if (n.link) window.location.href = n.link;
                      setOpen(false);
                    }}
                    className={cn(
                      "flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-neutral-50",
                      !n.read && "bg-primary-50/50",
                    )}
                  >
                    <Icon className="mt-0.5 h-4 w-4 shrink-0 text-neutral-400" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-neutral-700">{n.message}</p>
                      <p className="mt-0.5 text-xs text-neutral-400">
                        {new Date(n.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    {!n.read && (
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary-500" />
                    )}
                  </button>
                );
              })
            )}
          </div>

          <div className="border-t border-neutral-200 px-4 py-2">
            <Link
              href="/notifications"
              className="block text-center text-xs font-medium text-primary-600 hover:text-primary-700"
              onClick={() => setOpen(false)}
            >
              View all notifications
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
