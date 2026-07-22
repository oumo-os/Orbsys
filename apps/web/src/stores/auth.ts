import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface PlatformAccount {
  id: string;
  handle: string;
  legal_name: string | null;
}

interface OrgMember {
  id: string;
  handle: string;
  display_name: string;
  display_name_org?: string | null;
  org_id: string;
  org_slug?: string;
  org_name?: string;
  current_state: string;
}

interface AuthState {
  // Platform identity
  account: PlatformAccount | null;
  platformToken: string | null;
  platformRefreshToken: string | null;

  // Active org session
  member: OrgMember | null;
  orgSessionToken: string | null;

  // STF blind review
  isolatedToken: string | null;

  // Derived
  isAuthenticated: boolean;

  // Actions
  setPlatformAuth: (account: PlatformAccount, access: string, refresh: string) => void;
  setOrgSession: (member: OrgMember, token: string) => void;
  setIsolatedToken: (token: string | null) => void;
  clearOrgSession: () => void;
  logout: () => void;

  /** @deprecated legacy — kept so old code doesn't crash */
  setAuth: (member: OrgMember, access: string, refresh: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      account:              null,
      platformToken:        null,
      platformRefreshToken: null,
      member:               null,
      orgSessionToken:      null,
      isolatedToken:        null,
      isAuthenticated:      false,

      setPlatformAuth: (account, access, refresh) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("orbsys_platform_token",  access);
          localStorage.setItem("orbsys_refresh_token", refresh);
          localStorage.setItem("orbsys_access_token",  access);
        }
        set({
          account,
          platformToken:        access,
          platformRefreshToken: refresh,
          isAuthenticated:      true,
        });
      },

      setOrgSession: (member, token) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("orbsys_access_token", token);
          localStorage.setItem("orbsys_member", JSON.stringify(member));
        }
        set({ member, orgSessionToken: token });
      },

      setIsolatedToken: (token) => set({ isolatedToken: token }),

      clearOrgSession: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("orbsys_member");
          // Restore platform token as the active access token
          const platformToken = useAuthStore.getState().platformToken;
          if (platformToken) {
            localStorage.setItem("orbsys_access_token", platformToken);
          } else {
            localStorage.removeItem("orbsys_access_token");
          }
        }
        set({ member: null, orgSessionToken: null });
      },

      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("orbsys_access_token");
          localStorage.removeItem("orbsys_refresh_token");
          localStorage.removeItem("orbsys_member");
          localStorage.removeItem("orbsys_platform_token");
        }
        set({
          account:              null,
          platformToken:        null,
          platformRefreshToken: null,
          member:               null,
          orgSessionToken:      null,
          isolatedToken:        null,
          isAuthenticated:      false,
        });
      },

      // Legacy shim — called by bootstrap service / older components
      setAuth: (member, access, refresh) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("orbsys_platform_token",  access);
          localStorage.setItem("orbsys_access_token",  access);
          localStorage.setItem("orbsys_refresh_token", refresh);
          localStorage.setItem("orbsys_member", JSON.stringify(member));
        }
        set({
          member,
          account:               member as unknown as PlatformAccount,
          orgSessionToken:      access,
          platformToken:        access,
          platformRefreshToken: refresh,
          isAuthenticated:      true,
        });
      },
    }),
    {
      name:    "orbsys-auth",
      storage: createJSONStorage(() =>
        typeof window !== "undefined" ? localStorage : {
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {},
        }
      ),
      // Only persist non-sensitive shape — tokens stay in localStorage directly
      partialize: (s) => ({
        account:              s.account,
        member:               s.member,
        isAuthenticated:      s.isAuthenticated,
      }),
    }
  )
);
