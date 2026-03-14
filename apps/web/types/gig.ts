export interface Milestone {
  id: string;
  gig_id: string;
  title: string;
  description: string;
  amount: string;
  currency: string;
  status: string;
  order: number;
  due_date: string | null;
}

export interface Gig {
  id: string;
  client_id: string;
  client_name: string | null;
  client_avatar_url: string | null;
  client_wallet_address: string | null;
  freelancer_id: string | null;
  title: string;
  description: string;
  category: string | null;
  skills: string[];
  required_skills: string[];
  tags: string[];
  total_amount: string;
  currency: string;
  status: string;
  deadline: string | null;
  created_at: string;
  milestones: Milestone[];
}

export interface GigListResponse {
  gigs: Gig[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
