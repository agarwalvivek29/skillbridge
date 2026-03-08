import { apiGet, apiPost, apiPut, apiDelete } from "./client";
import type { PortfolioItem } from "@/types/portfolio";

export interface PortfolioPayload {
  title: string;
  description: string;
  project_url?: string;
  github_url?: string;
  cover_image_url?: string;
  tags: string[];
}

export function getMyPortfolio(): Promise<PortfolioItem[]> {
  return apiGet<PortfolioItem[]>("/v1/portfolio");
}

export function createPortfolioItem(
  payload: PortfolioPayload,
): Promise<PortfolioItem> {
  return apiPost<PortfolioItem>("/v1/portfolio", payload);
}

export function updatePortfolioItem(
  id: string,
  payload: PortfolioPayload,
): Promise<PortfolioItem> {
  return apiPut<PortfolioItem>(`/v1/portfolio/${id}`, payload);
}

export function deletePortfolioItem(id: string): Promise<void> {
  return apiDelete<void>(`/v1/portfolio/${id}`);
}

export function getUploadUrl(
  filename: string,
): Promise<{ upload_url: string; file_key: string }> {
  return apiGet<{ upload_url: string; file_key: string }>(
    `/v1/portfolio/upload-url?filename=${encodeURIComponent(filename)}`,
  );
}
