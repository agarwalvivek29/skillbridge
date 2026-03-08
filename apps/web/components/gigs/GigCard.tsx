"use client";

import Link from "next/link";
import { Calendar, Layers, DollarSign } from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar } from "@/components/ui/Avatar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { Gig } from "@/types/gig";

interface GigCardProps {
  gig: Gig;
  className?: string;
}

export function GigCard({ gig, className }: GigCardProps) {
  const milestoneCount = gig.milestones?.length ?? 0;
  const postedDate = new Date(gig.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <Link
      href={`/gigs/${gig.id}`}
      className={cn(
        "group block rounded-lg border border-neutral-200 bg-white p-4 shadow-sm transition-all hover:border-primary-200 hover:shadow-lg md:p-6",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-lg font-semibold text-neutral-800 group-hover:text-primary-600 transition-colors line-clamp-2">
          {gig.title}
        </h3>
        <StatusBadge status={gig.status} />
      </div>

      <div className="mt-3 flex items-center gap-2">
        <Avatar
          src={gig.client_avatar_url}
          name={gig.client_name}
          walletAddress={gig.client_wallet_address}
          size="xs"
        />
        <span className="text-sm text-neutral-500">
          {gig.client_name ?? "Anonymous"}
        </span>
      </div>

      {gig.skills.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {gig.skills.slice(0, 4).map((skill) => (
            <span
              key={skill}
              className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-600"
            >
              {skill}
            </span>
          ))}
          {gig.skills.length > 4 && (
            <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-400">
              +{gig.skills.length - 4}
            </span>
          )}
        </div>
      )}

      <div className="mt-4 flex items-center gap-4 text-sm text-neutral-500">
        <span className="inline-flex items-center gap-1">
          <DollarSign className="h-4 w-4" />
          {gig.total_amount} {gig.currency}
        </span>
        {milestoneCount > 0 && (
          <span className="inline-flex items-center gap-1">
            <Layers className="h-4 w-4" />
            {milestoneCount} milestone{milestoneCount !== 1 ? "s" : ""}
          </span>
        )}
        <span className="inline-flex items-center gap-1 ml-auto">
          <Calendar className="h-4 w-4" />
          {postedDate}
        </span>
      </div>
    </Link>
  );
}
