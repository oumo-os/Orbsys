"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [orgSlug, setOrgSlug] = useState("");
  const [handle, setHandle] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.post("/auth/login", {
        org_slug: orgSlug.trim(),
        handle: handle.trim(),
        password,
      });
      const { tokens, member } = res.data;
      setAuth(member, tokens.access_token, tokens.refresh_token);
      router.replace("/org/commons");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Login failed — check your credentials.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-orbsys-void px-4">
      <div className="w-full max-w-sm">
        {/* Logotype */}
        <div className="mb-8 text-center">
          <h1 className="font-display text-2xl tracking-tight text-orbsys-text">
            Orb Sys
          </h1>
          <p className="text-orbsys-muted text-xs mt-1 font-mono uppercase tracking-widest">
            Polycentric Governance
          </p>
        </div>

        <div className="card p-8">
          <p className="section-label mb-6">Sign in</p>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-orbsys-muted mb-1 uppercase tracking-wider">
                Organisation
              </label>
              <input
                type="text"
                value={orgSlug}
                onChange={(e) => setOrgSlug(e.target.value)}
                placeholder="your-org"
                required
                autoComplete="organization"
                className="w-full bg-orbsys-surface border border-orbsys-border rounded px-3 py-2 text-sm text-orbsys-text font-mono placeholder:text-orbsys-muted focus:outline-none focus:border-orbsys-gold transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-orbsys-muted mb-1 uppercase tracking-wider">
                Handle
              </label>
              <input
                type="text"
                value={handle}
                onChange={(e) => setHandle(e.target.value)}
                placeholder="your-handle"
                required
                autoComplete="username"
                className="w-full bg-orbsys-surface border border-orbsys-border rounded px-3 py-2 text-sm text-orbsys-text font-mono placeholder:text-orbsys-muted focus:outline-none focus:border-orbsys-gold transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-orbsys-muted mb-1 uppercase tracking-wider">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="w-full bg-orbsys-surface border border-orbsys-border rounded px-3 py-2 text-sm text-orbsys-text font-mono placeholder:text-orbsys-muted focus:outline-none focus:border-orbsys-gold transition-colors"
              />
            </div>

            {error && (
              <div className="text-xs font-mono text-red-400 bg-red-950/30 border border-red-800/40 rounded px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 rounded text-sm font-mono font-medium transition-all
                bg-orbsys-gold text-orbsys-void hover:brightness-110
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-orbsys-muted mt-6 font-mono">
          Access is by invitation only.
        </p>
      </div>
    </div>
  );
}
