import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});


export interface Listing {
  id:          string;
  source:      string;
  title:       string;
  price:       string;
  location:    string;
  url:         string;
  description: string;
  notified:    boolean;
  first_seen:  string;
  is_active:   boolean;
}

export interface ListingsPage {
  items:  Listing[];
  total:  number;
  page:   number;
  pages:  number;
}

export interface Deployment {
  id:           string;
  environment:  string;
  version:      string;
  image_tag:    string;
  deployed_by:  string;
  deployed_at:  string;
  is_current:   boolean;
  rollback_of:  string | null;
  notes:        string;
}

export interface CrawlRun {
  id:            number;
  started_at:    string;
  finished_at:   string | null;
  new_listings:  number;
  total_scraped: number;
  errors:        string;
  triggered_by:  string;
}

export interface HealthStatus {
  status:      string;
  environment: string;
  version:     string;
  db:          string;
}

export interface RollbackResponse {
  success:        boolean;
  new_deployment: Deployment;
  message:        string;
}


export const listingsApi = {
  getPage: (page = 1, perPage = 20, search = "") =>
    api.get<ListingsPage>("/listings", {
      params: { page, per_page: perPage, search: search || undefined },
    }).then(r => r.data),

  getCrawlRuns: (limit = 10) =>
    api.get<CrawlRun[]>("/listings/runs", { params: { limit } }).then(r => r.data),

  triggerCrawl: () =>
    api.post<{ run_id: number; message: string }>("/listings/crawl").then(r => r.data),
};

export const deploymentsApi = {
  getAll: (environment?: string) =>
    api.get<Deployment[]>("/deployments", {
      params: { environment: environment || undefined, limit: 30 },
    }).then(r => r.data),

  getCurrent: (environment: string) =>
    api.get<Deployment>(`/deployments/current/${environment}`).then(r => r.data),

  rollback: (targetId: string, reason = "") =>
    api.post<RollbackResponse>("/deployments/rollback", {
      target_deployment_id: targetId,
      reason,
    }).then(r => r.data),
};

export const healthApi = {
  get: () => api.get<HealthStatus>("/health").then(r => r.data),
};
