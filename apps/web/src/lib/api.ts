import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

// Attach JWT from store on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("orbsys_access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 → clear session and redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("orbsys_access_token");
      localStorage.removeItem("orbsys_refresh_token");
      localStorage.removeItem("orbsys_member");
      window.location.href = "/auth/login";
    }
    return Promise.reject(err);
  }
);

// ── Typed endpoints ───────────────────────────────────────────────────────────

export const authApi = {
  login: (org_slug: string, handle: string, password: string) =>
    api.post("/auth/login", { org_slug, handle, password }),
  refresh: (refresh_token: string) =>
    api.post("/auth/refresh", { refresh_token }),
  register: (org_slug: string, data: object) =>
    api.post(`/auth/register?org_slug=${org_slug}`, data),
};

export const membersApi = {
  me: () => api.get("/members/me"),
  feed: (params?: { page?: number; dormain_id?: string }) =>
    api.get("/members/me/feed", { params }),
  curiosities: () => api.get("/members/me/curiosities"),
  setCuriosities: (data: Record<string, number>) =>
    api.put("/members/me/curiosities", data),
  notifications: (params?: { unread_only?: boolean; page?: number; page_size?: number }) =>
    api.get("/members/me/notifications", { params }),
  markRead: (id: string) =>
    api.post(`/members/me/notifications/${id}/read`),
  markAllRead: () =>
    api.post("/members/me/notifications/read-all"),
};

export const competenceApi = {
  dormains: () => api.get("/competence/dormains"),
  leaderboard: (dormain_id: string, params?: { page?: number }) =>
    api.get(`/competence/leaderboard/${dormain_id}`, { params }),
  myScores: () => api.get("/competence/scores/me"),
  myWhClaims: () => api.get("/competence/wh-claims/me"),
  submitWhClaim: (data: object) => api.post("/competence/wh-claims", data),
};

export const commonsApi = {
  threads: (params?: object) => api.get("/commons/threads", { params }),
  thread: (id: string) => api.get(`/commons/threads/${id}`),
  createThread: (data: object) => api.post("/commons/threads", data),
  posts: (thread_id: string, params?: object) =>
    api.get(`/commons/threads/${thread_id}/posts`, { params }),
  createPost: (thread_id: string, data: object) =>
    api.post(`/commons/threads/${thread_id}/posts`, data),
  sponsorDraft: (thread_id: string) =>
    api.post(`/commons/threads/${thread_id}/sponsor`),
  confirmSponsor: (thread_id: string, data: object) =>
    api.post(`/commons/threads/${thread_id}/sponsor/confirm`, data),
  formalReview: (post_id: string, data: object) =>
    api.post(`/commons/posts/${post_id}/formal-review`, data),
  correctTag: (thread_id: string, data: object) =>
    api.post(`/commons/threads/${thread_id}/correct-tag`, data),
};

export const cellsApi = {
  get: (id: string) => api.get(`/cells/${id}`),
  contributions: (id: string, params?: object) =>
    api.get(`/cells/${id}/contributions`, { params }),
  addContribution: (id: string, data: object) =>
    api.post(`/cells/${id}/contributions`, data),
  importContext: (id: string, data: object) =>
    api.post(`/cells/${id}/import-commons-context`, data),
  minutes: (id: string) => api.get(`/cells/${id}/minutes`),
  votes: (id: string) => api.get(`/cells/${id}/votes`),
  castVote: (id: string, data: object) => api.post(`/cells/${id}/votes`, data),
  crystallise: (id: string) => api.post(`/cells/${id}/crystallise`),
  fileMotion: (id: string, data: object) =>
    api.post(`/cells/${id}/file-motion`, data),
  compositionProfile: (id: string) =>
    api.get(`/cells/${id}/composition-profile`),
  dissolve: (id: string, data: object) =>
    api.post(`/cells/${id}/dissolve`, data),
};

export const motionsApi = {
  get: (id: string) => api.get(`/motions/${id}`),
  validateSpec: (id: string, data: object) =>
    api.post(`/motions/${id}/validate-specification`, data),
};

export const stfApi = {
  list: (params?: object) => api.get("/stf", { params }),
  get: (id: string) => api.get(`/stf/${id}`),
  commission: (data: object) => api.post("/stf", data),
  assignments: (id: string) => api.get(`/stf/${id}/assignments`),
  verdicts: (id: string) => api.get(`/stf/${id}/verdicts`),
  verdictRationales: (id: string) => api.get(`/stf/${id}/verdicts/rationales`),
  enact: (id: string, resolution_id: string) =>
    api.post(`/stf/${id}/resolutions`, {
      resolution_id,
      confirmation: "ENACT",
    }),
};

export const circlesApi = {
  list: () => api.get("/circles"),
  get: (id: string) => api.get(`/circles/${id}`),
  members: (id: string) => api.get(`/circles/${id}/members`),
  health: (id: string) => api.get(`/circles/${id}/health`),
  invite: (id: string, data: object) => api.post(`/circles/${id}/members`, data),
};

export const orgApi = {
  get: () => api.get("/org"),
  parameters: () => api.get("/org/parameters"),
  dormains: () => api.get("/org/dormains"),
  createDormain: (data: object) => api.post("/org/dormains", data),
};

export const ledgerApi = {
  events: (params?: object) => api.get("/ledger", { params }),
  event: (id: string) => api.get(`/ledger/${id}`),
  verify: () => api.get("/ledger/verify"),
  auditArchive: (params?: object) =>
    api.get("/ledger/audit-archive", { params }),
};
