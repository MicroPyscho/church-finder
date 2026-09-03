import axios from "axios";

const BASE = import.meta.env.VITE_API_URL || "";;

export const api = axios.create({
  baseURL: BASE,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use(cfg => {
  const t = localStorage.getItem("sanctuary_token");
  if (t && cfg.headers) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

export const propertyApi = {
  get:      (id: string) => api.get(`/api/properties/${id}`).then(r => r.data),
  analysis: (id: string) => api.get(`/api/properties/${id}/analysis`).then(r => r.data),
};

export const favouritesApi = {
  list:   ()           => api.get("/api/favourites").then(r => r.data),
  add:    (id: string) => api.post(`/api/favourites/${id}`, {}).then(r => r.data),
  remove: (id: string) => api.delete(`/api/favourites/${id}`).then(r => r.data),
  bulk:   ()           => api.post("/api/favourites/bulk-interest").then(r => r.data),
};

export const alertsApi = {
  list:   ()           => api.get("/api/alerts").then(r => r.data),
  create: (b: any)     => api.post("/api/alerts", b).then(r => r.data),
  delete: (id: number) => api.delete(`/api/alerts/${id}`).then(r => r.data),
};

export const outreachApi = {
  draft: (b: any) => api.post("/api/outreach/draft", b).then(r => r.data),
  send:  (b: any) => api.post("/api/outreach/send",  b).then(r => r.data),
};

export const authApi = {
  register: (b: any) => api.post("/api/auth/register", b).then(r => r.data),
  login:    (b: any) => api.post("/api/auth/login",    b).then(r => r.data),
  me:       ()       => api.get("/api/auth/me").then(r => r.data),
};