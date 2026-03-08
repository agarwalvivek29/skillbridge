import { apiGet, apiPut } from "./client";
import type { Notification } from "@/types/notification";

export interface NotificationsResponse {
  notifications: Notification[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export function getNotifications(params: {
  page?: number;
  limit?: number;
  unread?: boolean;
  type?: string;
}): Promise<NotificationsResponse> {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.unread) qs.set("unread", "true");
  if (params.type) qs.set("type", params.type);
  return apiGet<NotificationsResponse>(`/v1/notifications?${qs.toString()}`);
}

export function markNotificationRead(id: string): Promise<void> {
  return apiPut<void>(`/v1/notifications/${id}/read`);
}

export function markAllNotificationsRead(): Promise<void> {
  return apiPut<void>("/v1/notifications/read-all");
}
