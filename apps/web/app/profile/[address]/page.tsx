"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import {
  Star,
  Shield,
  Award,
  Briefcase,
  DollarSign,
  AlertTriangle,
  ExternalLink,
  BadgeCheck,
  Github,
  FolderOpen,
} from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { AddressDisplay } from "@/components/web3/AddressDisplay";
import { getPublicProfile } from "@/lib/api/profile";
import { formatRole, isFreelancer } from "@/lib/format";
import type { PublicProfile } from "@/types/profile";

const tierColors: Record<string, { bg: string; text: string; border: string }> =
  {
    BRONZE: {
      bg: "bg-[#FFF7ED]",
      text: "text-[#9A3412]",
      border: "border-[#FED7AA]",
    },
    SILVER: {
      bg: "bg-neutral-100",
      text: "text-neutral-700",
      border: "border-neutral-300",
    },
    GOLD: {
      bg: "bg-[#FFFBEB]",
      text: "text-[#92400E]",
      border: "border-[#FDE68A]",
    },
    PLATINUM: {
      bg: "bg-web3-50",
      text: "text-[#5B21B6]",
      border: "border-web3-200",
    },
  };

export default function PublicProfilePage() {
  const { address } = useParams<{ address: string }>();
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!address) return;
    setLoading(true);
    getPublicProfile(address)
      .then(setProfile)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [address]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="mx-auto max-w-[1280px] px-4 py-16 md:px-6">
        <EmptyState
          icon={AlertTriangle}
          title="Profile not found"
          description={error ?? "This user profile does not exist."}
        />
      </div>
    );
  }

  const tier = tierColors[profile.badge_tier] ?? tierColors.BRONZE;

  return (
    <div className="mx-auto max-w-[1280px] px-4 py-8 md:px-6 md:py-16">
      {/* Header */}
      <Card className="mb-8">
        <div className="flex flex-col items-start gap-6 md:flex-row md:items-center">
          <Avatar
            src={profile.avatar_url}
            name={profile.display_name}
            walletAddress={profile.wallet_address}
            size="xl"
          />
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-bold text-neutral-800">
                {profile.display_name ?? "Anonymous"}
              </h1>
              <Badge variant={isFreelancer(profile.role) ? "primary" : "info"}>
                {formatRole(profile.role)}
              </Badge>
            </div>
            <div className="mt-2">
              <AddressDisplay address={profile.wallet_address} />
            </div>
            <p className="mt-2 text-sm text-neutral-500">
              Member since {new Date(profile.member_since).toLocaleDateString()}
            </p>
            {profile.bio && (
              <p className="mt-3 text-sm text-neutral-600">{profile.bio}</p>
            )}
          </div>

          {/* Reputation score */}
          <div className="flex flex-col items-center">
            <div className="text-4xl font-bold text-neutral-800">
              {profile.reputation_score}
            </div>
            <span
              className={`mt-1 inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium ${tier.bg} ${tier.text} ${tier.border}`}
            >
              <Shield className="h-3 w-3" />
              {profile.badge_tier}
            </span>
          </div>
        </div>
      </Card>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          {/* Stats */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Card className="text-center">
              <Briefcase className="mx-auto h-5 w-5 text-neutral-400" />
              <div className="mt-2 text-2xl font-bold text-neutral-800">
                {profile.gigs_completed}
              </div>
              <div className="text-xs text-neutral-500">Gigs Completed</div>
            </Card>
            <Card className="text-center">
              <DollarSign className="mx-auto h-5 w-5 text-neutral-400" />
              <div className="mt-2 text-2xl font-bold text-neutral-800">
                {isFreelancer(profile.role)
                  ? (profile.total_earned ?? "0")
                  : (profile.total_spent ?? "0")}{" "}
                ETH
              </div>
              <div className="text-xs text-neutral-500">
                {isFreelancer(profile.role) ? "Total Earned" : "Total Spent"}
              </div>
            </Card>
            <Card className="text-center">
              <Star className="mx-auto h-5 w-5 text-secondary-400" />
              <div className="mt-2 text-2xl font-bold text-neutral-800">
                {profile.avg_rating?.toFixed(1) ?? "N/A"}
              </div>
              <div className="text-xs text-neutral-500">Avg Rating</div>
            </Card>
            <Card className="text-center">
              <AlertTriangle className="mx-auto h-5 w-5 text-neutral-400" />
              <div className="mt-2 text-2xl font-bold text-neutral-800">
                {profile.dispute_rate != null
                  ? `${(profile.dispute_rate * 100).toFixed(0)}%`
                  : "0%"}
              </div>
              <div className="text-xs text-neutral-500">Dispute Rate</div>
            </Card>
          </div>

          {/* Skills */}
          {profile.skills.length > 0 && (
            <section>
              <h2 className="mb-4 text-lg font-semibold text-neutral-800">
                Skills
              </h2>
              <div className="flex flex-wrap gap-2">
                {profile.skills.map((skill) => (
                  <Badge key={skill} variant="default">
                    {skill}
                  </Badge>
                ))}
              </div>
            </section>
          )}

          {/* On-chain badges */}
          {profile.on_chain_badges.length > 0 && (
            <section>
              <h2 className="mb-4 text-lg font-semibold text-neutral-800">
                On-Chain Badges
              </h2>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
                {profile.on_chain_badges.map((badge) => (
                  <Card key={badge.id} className="text-center">
                    <Award className="mx-auto h-8 w-8 text-web3-500" />
                    <div className="mt-2 text-sm font-medium text-neutral-800">
                      {badge.name}
                    </div>
                    <div className="mt-1 text-xs text-neutral-500">
                      {badge.description}
                    </div>
                    <div className="mt-2 text-xs text-neutral-400">
                      {new Date(badge.earned_at).toLocaleDateString()}
                    </div>
                  </Card>
                ))}
              </div>
            </section>
          )}

          {/* Portfolio */}
          {profile.portfolio_items.length > 0 && (
            <section>
              <h2 className="mb-4 text-lg font-semibold text-neutral-800">
                Portfolio
              </h2>
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {profile.portfolio_items.map((item) => (
                  <Card
                    key={item.id}
                    className="flex flex-col overflow-hidden border border-neutral-200 p-0 transition-shadow hover:shadow-md"
                  >
                    {/* Cover image / URL preview / placeholder */}
                    <div className="relative h-44 bg-gradient-to-br from-primary-50 to-web3-50">
                      {item.cover_image_url ? (
                        <Image
                          src={item.cover_image_url}
                          alt={item.title}
                          fill
                          className="object-cover"
                        />
                      ) : item.external_url || item.project_url ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={`https://api.microlink.io/?url=${encodeURIComponent((item.external_url || item.project_url)!)}&screenshot=true&meta=false&embed=screenshot.url`}
                          alt={`Preview of ${item.title}`}
                          className="h-full w-full object-cover"
                          onError={(e) => {
                            e.currentTarget.style.display = "none";
                          }}
                        />
                      ) : item.github_url ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={`https://opengraph.githubassets.com/1/${item.github_url.replace("https://github.com/", "")}`}
                          alt={`GitHub preview of ${item.title}`}
                          className="h-full w-full object-cover"
                          onError={(e) => {
                            e.currentTarget.style.display = "none";
                          }}
                        />
                      ) : (
                        <div className="flex h-full items-center justify-center">
                          <FolderOpen className="h-12 w-12 text-primary-200" />
                        </div>
                      )}
                      {item.verified_delivery && (
                        <span className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-green-500 px-2.5 py-1 text-xs font-medium text-white shadow-sm">
                          <BadgeCheck className="h-3.5 w-3.5" />
                          Verified
                        </span>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex flex-1 flex-col p-4">
                      <h3 className="text-base font-semibold text-neutral-800">
                        {item.title}
                      </h3>
                      <p className="mt-1.5 line-clamp-3 flex-1 text-sm leading-relaxed text-neutral-500">
                        {item.description}
                      </p>

                      {/* Tags */}
                      {item.tags && item.tags.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {item.tags.map((tag) => (
                            <Badge key={tag} variant="default">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}

                      {/* Links */}
                      {(item.external_url ||
                        item.project_url ||
                        item.github_url) && (
                        <div className="mt-4 flex items-center gap-3 border-t border-neutral-100 pt-3">
                          {(item.external_url || item.project_url) && (
                            <a
                              href={(item.external_url || item.project_url)!}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 text-sm font-medium text-primary-600 transition-colors hover:text-primary-700"
                            >
                              <ExternalLink className="h-4 w-4" />
                              Live Demo
                            </a>
                          )}
                          {item.github_url && (
                            <a
                              href={item.github_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-800"
                            >
                              <Github className="h-4 w-4" />
                              Source
                            </a>
                          )}
                        </div>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            </section>
          )}

          {/* Reviews */}
          {profile.reviews.length > 0 && (
            <section>
              <h2 className="mb-4 text-lg font-semibold text-neutral-800">
                Reviews
              </h2>
              <div className="space-y-4">
                {profile.reviews.map((review) => (
                  <Card key={review.id}>
                    <div className="flex items-start gap-3">
                      <Avatar
                        src={review.reviewer_avatar}
                        name={review.reviewer_name}
                        size="sm"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-neutral-800">
                            {review.reviewer_name ?? "Anonymous"}
                          </span>
                          <div className="flex items-center gap-0.5">
                            {Array.from({ length: 5 }).map((_, i) => (
                              <Star
                                key={i}
                                className={`h-3.5 w-3.5 ${
                                  i < review.score
                                    ? "fill-secondary-400 text-secondary-400"
                                    : "text-neutral-300"
                                }`}
                              />
                            ))}
                          </div>
                          <span className="text-xs text-neutral-400">
                            {new Date(review.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        {review.review && (
                          <p className="mt-1 text-sm text-neutral-600">
                            {review.review}
                          </p>
                        )}
                        {review.tags.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {review.tags.map((tag) => (
                              <Badge key={tag} variant="default">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Sidebar - Active gigs (client) */}
        <div className="space-y-8">
          {profile.active_gigs.length > 0 && (
            <section>
              <h2 className="mb-4 text-lg font-semibold text-neutral-800">
                Active Gigs
              </h2>
              <div className="space-y-3">
                {profile.active_gigs.map((gig) => (
                  <Link key={gig.id} href={`/gigs/${gig.id}`}>
                    <Card className="transition-shadow hover:shadow-lg">
                      <h3 className="text-sm font-medium text-neutral-800">
                        {gig.title}
                      </h3>
                      <div className="mt-2 flex items-center justify-between">
                        <StatusBadge status={gig.status} />
                        <span className="text-sm font-semibold text-neutral-700">
                          {gig.budget} ETH
                        </span>
                      </div>
                    </Card>
                  </Link>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
