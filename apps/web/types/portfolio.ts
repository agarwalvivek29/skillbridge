export interface PortfolioItem {
  id: string;
  user_id: string;
  title: string;
  description: string;
  project_url: string | null;
  github_url: string | null;
  cover_image_url: string | null;
  tags: string[];
  verified_delivery: boolean;
  gig_id: string | null;
  created_at: string;
}
