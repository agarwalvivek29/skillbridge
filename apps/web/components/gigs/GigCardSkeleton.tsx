import { cn } from "@/lib/utils";

interface GigCardSkeletonProps {
  className?: string;
}

export function GigCardSkeleton({ className }: GigCardSkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-lg border border-neutral-200 bg-white p-4 shadow-sm md:p-6",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="h-5 w-3/4 rounded bg-neutral-200" />
        <div className="h-5 w-16 rounded-full bg-neutral-200" />
      </div>

      <div className="mt-3 flex items-center gap-2">
        <div className="h-6 w-6 rounded-full bg-neutral-200" />
        <div className="h-4 w-24 rounded bg-neutral-200" />
      </div>

      <div className="mt-3 flex gap-1.5">
        <div className="h-5 w-14 rounded-full bg-neutral-200" />
        <div className="h-5 w-16 rounded-full bg-neutral-200" />
        <div className="h-5 w-12 rounded-full bg-neutral-200" />
      </div>

      <div className="mt-4 flex items-center gap-4">
        <div className="h-4 w-20 rounded bg-neutral-200" />
        <div className="h-4 w-24 rounded bg-neutral-200" />
        <div className="ml-auto h-4 w-20 rounded bg-neutral-200" />
      </div>
    </div>
  );
}
