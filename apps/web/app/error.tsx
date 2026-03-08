"use client";

import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <AlertTriangle className="h-12 w-12 text-error-500" />
      <h2 className="mt-4 text-2xl font-bold text-neutral-800">
        Something went wrong
      </h2>
      <p className="mt-2 text-sm text-neutral-500">
        {error.message || "An unexpected error occurred."}
      </p>
      <Button variant="primary" size="md" onClick={reset} className="mt-6">
        Try again
      </Button>
    </div>
  );
}
