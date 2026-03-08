"use client";

import { CheckCircle, XCircle, AlertTriangle, Info, X } from "lucide-react";
import { useToastStore, type ToastType } from "@/hooks/useToast";
import { cn } from "@/lib/utils";

const iconMap: Record<ToastType, typeof CheckCircle> = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const borderColorMap: Record<ToastType, string> = {
  success: "border-l-success-500",
  error: "border-l-error-500",
  warning: "border-l-warning-500",
  info: "border-l-info-500",
};

const iconColorMap: Record<ToastType, string> = {
  success: "text-success-500",
  error: "text-error-500",
  warning: "text-warning-500",
  info: "text-info-500",
};

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed right-4 top-4 z-[100] flex flex-col gap-2">
      {toasts.map((toast) => {
        const Icon = iconMap[toast.type];
        return (
          <div
            key={toast.id}
            role="alert"
            aria-live="polite"
            className={cn(
              "flex w-[400px] max-w-[calc(100vw-2rem)] items-start gap-3 rounded-lg border-l-4 bg-white p-4 shadow-lg",
              borderColorMap[toast.type],
            )}
          >
            <Icon
              className={cn(
                "mt-0.5 h-5 w-5 shrink-0",
                iconColorMap[toast.type],
              )}
            />
            <p className="flex-1 text-sm text-neutral-700">{toast.message}</p>
            <button
              onClick={() => removeToast(toast.id)}
              className="shrink-0 rounded p-0.5 text-neutral-400 hover:text-neutral-600"
              aria-label="Dismiss"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
