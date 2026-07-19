import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  withCredentials: false,
});

// Attach JWT from localStorage on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("orbsys_access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 handling:
//   - Platform token expired → refresh and retry
//   - Org session token expired → redirect to login (no refresh available)
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const status = err.response?.status;
    const url    = err.config?.url ?? "";

    // Don't retry the refresh call itself
    if (url.includes("/auth/refresh-platform")) {
      localStorage.clear();
      if (typeof window !== "undefined") window.location.href = "/auth/login";
      return Promise.reject(err);
    }

    if (status === 401 && typeof window !== "undefined") {
      // Already retried — don't loop
      if (err.config?._retry) {
        localStorage.removeItem("orbsys_access_token");
        localStorage.removeItem("orbsys_refresh_token");
        localStorage.removeItem("orbsys_member");
        window.location.href = "/auth/login";
        return Promise.reject(err);
      }

      const inOrgSession = !!localStorage.getItem("orbsys_member");

      if (inOrgSession) {
        // Org session token is invalid/expired — no platform refresh can help.
        // Clear and send to login so the user can re-enter the org.
        localStorage.removeItem("orbsys_access_token");
        localStorage.removeItem("orbsys_refresh_token");
        localStorage.removeItem("orbsys_member");
        window.location.href = "/auth/login";
        return Promise.reject(err);
      }

      // Platform session — try refresh
      const refreshToken = localStorage.getItem("orbsys_refresh_token");
      if (refreshToken) {
        try {
          err.config._retry = true;
          const res = await axios.post(`${API_URL}/auth/refresh-platform`, {
            refresh_token: refreshToken,
          });
          const newToken = res.data.access_token;
          localStorage.setItem("orbsys_access_token", newToken);
          api.defaults.headers.common["Authorization"] = `Bearer ${newToken}`;
          err.config.headers["Authorization"] = `Bearer ${newToken}`;
          return api.request(err.config);
        } catch {
          localStorage.removeItem("orbsys_access_token");
          localStorage.removeItem("orbsys_refresh_token");
          localStorage.removeItem("orbsys_member");
          window.location.href = "/auth/login";
        }
      } else {
        window.location.href = "/auth/login";
      }
    }
    return Promise.reject(err);
  }
);

// ── Platform auth ──────────────────────────────────────────────────────────────
export const platformApi = {
  login:    (handle_or_email: string, password: string) =>
    api.post("/auth/login", { handle_or_email, password }),
  register: (handle: string, email: string, password: string, legal_name?: string) =>
    api.post("/auth/register-account", { handle, email, password, legal_name }),
  enterOrg: (org_id: string) =>
    api.post(`/auth/enter-org/${org_id}`),
  refresh:  (refresh_token: string) =>
    api.post("/auth/refresh-platform", { refresh_token }),
};

export const accountApi = {
  me:          () => api.get("/accounts/me"),
  myOrgs:      () => api.get("/accounts/me/orgs"),
  wallet:      () => api.get("/accounts/me/wallet"),
  addWallet:   (data: object) => api.post("/accounts/me/wallet", data),
  setLegalName:(data: object) => api.post("/accounts/me/legal-name", data),
};

// ── Org-session endpoints (require org session token) ────────────────────────
export const membersApi = {
  me: () => api.get("/members/me"),
  feed: (params?: object) => api.get("/members/me/feed", { params }),
  curiosities: () => api.get("/members/me/curiosities"),
  setCuriosities: (data: object) => api.put("/members/me/curiosities", data),
  notifications: (params?: object) => api.get("/members/me/notifications", { params }),
  markRead: (id: string) => api.post(`/members/me/notifications/${id}/read`),
  markAllRead: () => api.post("/members/me/notifications/read-all"),
  applications: (params?: object) => api.get("/members/applications", { params }),
  reviewApplication: (id: string, data: object) =>
    api.post(`/members/applications/${id}/review`, data),
};

export const commonsApi = {
  threads: (params?: object) => api.get("/commons/threads", { params }),
  thread:  (id: string) => api.get(`/commons/threads/${id}`),
  posts:   (id: string, params?: object) => api.get(`/commons/threads/${id}/posts`, { params }),
  createPost: (id: string, data: object) => api.post(`/commons/threads/${id}/posts`, data),
  create:  (data: object) => api.post("/commons/threads", data),
  sponsor: (id: string) => api.post(`/commons/threads/${id}/sponsor`),
  confirmSponsor: (id: string, data: object) =>
    api.post(`/commons/threads/${id}/sponsor/confirm`, data),
  sponsorDraft: (id: string) => api.get(`/commons/threads/${id}/sponsor-draft`),
  formalReview: (postId: string, data: object) =>
    api.post(`/commons/posts/${postId}/formal-review`, data),
  tagSuggestions: (id: string) =>
    api.get(`/commons/threads/${id}/dormain-tag-suggestions`),
};

export const cellsApi = {
  list: (params?: object) => api.get("/cells", { params }),
  get: (id: string) => api.get(`/cells/${id}`),
  contributions: (id: string, params?: object) =>
    api.get(`/cells/${id}/contributions`, { params }),
  contribute: (id: string, data: object) => api.post(`/cells/${id}/contributions`, data),
  addContribution: (id: string, data: object) => api.post(`/cells/${id}/contributions`, data),
  votes: (id: string) => api.get(`/cells/${id}/votes`),
  vote: (id: string, data: object) => api.post(`/cells/${id}/votes`, data),
  castVote: (id: string, data: object) => api.post(`/cells/${id}/votes`, data),
  crystallise: (id: string) => api.post(`/cells/${id}/crystallise`),
  fileMotion: (id: string, data: object) => api.post(`/cells/${id}/file-motion`, data),
  minutes: (id: string) => api.get(`/cells/${id}/minutes`),
  create: (data: object) => api.post("/cells", data),
};

export const circlesApi = {
  list: () => api.get("/circles"),
  get: (id: string) => api.get(`/circles/${id}`),
  members: (id: string) => api.get(`/circles/${id}/members`),
  invite: (id: string, data: object) => api.post(`/circles/${id}/members`, data),
  health: (id: string) => api.get(`/circles/${id}/health`),
};

export const competenceApi = {
  dormains: () => api.get("/competence/dormains"),
  scores: () => api.get("/competence/scores/me"),
  leaderboard: (dormainId: string, params?: object) =>
    api.get(`/competence/leaderboard/${dormainId}`, { params }),
  whClaims: () => api.get("/competence/wh-claims/me"),
  submitWh: (data: object) => api.post("/competence/wh-claims", data),
};

export const motionsApi = {
  list: (params?: object) => api.get("/motions", { params }),
  get: (id: string) => api.get(`/motions/${id}`),
  validate: (id: string, data: object) =>
    api.post(`/motions/${id}/validate-specification`, data),
};

export const stfApi = {
  list: (params?: object) => api.get("/stf", { params }),
  get: (id: string) => api.get(`/stf/${id}`),
  assignments: (id: string) => api.get(`/stf/${id}/assignments`),
  verdicts: (id: string) => api.get(`/stf/${id}/verdicts`),
  enact: (id: string) => api.post(`/stf/${id}/resolutions`),
};

export const orgApi = {
  get: () => api.get("/org"),
  parameters: () => api.get("/org/parameters"),
  dormains: () => api.get("/org/dormains"),
  circles: () => api.get("/circles"),
};

export const ledgerApi = {
  events: (params?: object) => api.get("/ledger", { params }),
  verify: () => api.get("/ledger/verify"),
};

export const invitationApi = {
  get:    (token: string) => api.get(`/invitations/${token}`),
  accept: (token: string, data?: { handle?: string; display_name?: string }) =>
    api.post(`/invitations/${token}/accept`, data ?? {}),
};
