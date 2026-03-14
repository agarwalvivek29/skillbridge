/**
 * @proto packages/schema/proto/api/v1/portfolio.proto — PortfolioItem
 *
 * Field mappings:
 *   id                = proto PortfolioItem.id
 *   user_id           = proto PortfolioItem.user_id
 *   title             = proto PortfolioItem.title
 *   description       = proto PortfolioItem.description
 *   external_url      = proto PortfolioItem.external_url
 *   tags              = proto PortfolioItem.tags
 *   is_verified      ← proto PortfolioItem.verified_gig_id (non-empty → true)
 *   gig_id            ← proto PortfolioItem.verified_gig_id
 *   created_at        = proto PortfolioItem.created_at (Timestamp → ISO string)
 *
 * Frontend-only / API-enriched fields:
 *   github_url        — API-enriched (not in proto)
 *   cover_image_url   — API-enriched (not in proto; proto uses file_keys for uploads)
 *
 * Proto fields NOT mapped:
 *   PortfolioItem.file_keys, PortfolioItem.updated_at
 */
export interface PortfolioItem {
  id: string;
  user_id: string;
  title: string;
  description: string;
  external_url: string | null;
  github_url: string | null;
  cover_image_url: string | null;
  tags: string[];
  is_verified: boolean;
  gig_id: string | null;
  created_at: string;
}
