import { create } from "zustand";
import { api } from "@/lib/api";

interface Member {
  id: string;
  handle: string;
  display_name: string;
  org_id: string;
  current_state: string;
  joined_at: string;
}

interface AuthState {
  member: Member | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isHydrated: boolean;

  setAuth: (member: Member, accessToken: string, refreshToken: string) => void;
  clearAuth: () => void;
  hydrate: () => void;
  refreshAccess: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  member: null,
  accessToken: null,
  isAuthenticated: false,
  isHydrated: false,

  setAuth: (member, accessToken, refreshToken) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("orbsys_access_token", accessToken);
      localStorage.setItem("orbsys_refresh_token", refreshToken);
      localStorage.setItem("orbsys_member", JSON.stringify(member));
    }
    api.defaults.headers.common["Authorization"] = `Bearer ${accessToken}`;
    set({ member, accessToken, isAuthenticated: true });
  },

  clearAuth: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("orbsys_access_token");
      localStorage.removeItem("orbsys_refresh_token");
      localStorage.removeItem("orbsys_member");
    }
    delete api.defaults.headers.common["Authorization"];
    set({ member: null, accessToken: null, isAuthenticated: false });
  },

  hydrate: () => {
    if (typeof window === "undefined") {
      set({ isHydrated: true });
      return;
    }
    const token = localStorage.getItem("orbsys_access_token");
    const memberRaw = localStorage.getItem("orbsys_member");
    if (token && memberRaw) {
      try {
        const member = JSON.parse(memberRaw) as Member;
        api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
        set({ member, accessToken: token, isAuthenticated: true });
      } catch {
        // corrupted — clear
        localStorage.removeItem("orbsys_access_token");
        localStorage.removeItem("orbsys_refresh_token");
        localStorage.removeItem("orbsys_member");
      }
    }
    set({ isHydrated: true });
  },

  refreshAccess: async () => {
    const refreshToken =
      typeof window !== "undefined"
        ? localStorage.getItem("orbsys_refresh_token")
        : null;
    if (!refreshToken) return false;
    try {
      const res = await api.post("/auth/refresh", {
        refresh_token: refreshToken,
      });
      const { access_token, refresh_token: newRefresh } = res.data;
      const member = get().member;
      if (member) {
        get().setAuth(member, access_token, newRefresh);
      }
      return true;
    } catch {
      get().clearAuth();
      return false;
    }
  },
}));
