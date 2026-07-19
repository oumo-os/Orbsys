"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { platformApi, accountApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const T = {
  bg:"#050505", surface:"#080808", border:"#141414",
  gold:"#c8a96e", muted:"#3a3a3a", textDim:"#555555",
  text:"#cccccc", textSub:"#888888",
  mono:"'DM Mono', monospace", serif:"'Lora', serif",
};

export default function LoginPage() {
  const router = useRouter();
  const { setPlatformAuth, setOrgSession } = useAuthStore();

  const [identifier, setIdentifier] = useState("");
  const [password,   setPassword]   = useState("");
  const [error,      setError]      = useState<string | null>(null);
  const [loading,    setLoading]    = useState(false);

  async function login() {
    if (!identifier.trim() || !password) return;
    setLoading(true); setError(null);
    try {
      // 1. Platform login
      const res  = await platformApi.login(identifier.trim(), password);
      const data = res.data;
      setPlatformAuth(
        data.account,
        data.tokens.access_token,
        data.tokens.refresh_token
      );

      // 2. Load org memberships
      const orgsRes = await accountApi.myOrgs();
      const orgs    = orgsRes.data?.items ?? [];

      if (orgs.length === 0) {
        // No memberships — go to personal dashboard / org discovery
        router.replace("/me");
        return;
      }

      if (orgs.length === 1) {
        // Auto-enter the only org
        await enterOrg(orgs[0]);
      } else {
        // Multiple orgs — let them choose
        router.replace("/me");
      }
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setError(detail === "INVALID_CREDENTIALS"
        ? "Invalid handle or password."
        : detail ?? "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  async function enterOrg(org: { org_id: string; member_id: string; org_slug: string; org_name: string; display_name_org?: string; handle?: string; current_state: string }) {
    const { platformApi: pApi, api } = await import("@/lib/api");
    const sessionRes = await (await import("@/lib/api")).platformApi.enterOrg(org.org_id);
    const sessionToken = sessionRes.data.org_session_token;
    setOrgSession({
      id:             org.member_id,
      handle:         org.handle ?? "",
      display_name:   org.display_name_org ?? "",
      display_name_org: org.display_name_org,
      org_id:         org.org_id,
      org_slug:       org.org_slug,
      org_name:       org.org_name,
      current_state:  org.current_state,
    }, sessionToken);
    router.replace("/org/commons");
  }

  return (
    <div style={{
      minHeight:"100vh", background:T.bg, display:"flex",
      alignItems:"center", justifyContent:"center",
      fontFamily:T.mono,
    }}>
      <div style={{
        width:320, padding:"32px 28px",
        background:T.surface, border:`1px solid ${T.border}`,
        borderRadius:8,
      }}>
        <div style={{ marginBottom:28 }}>
          <p style={{ margin:"0 0 4px", fontSize:11, letterSpacing:4,
            textTransform:"uppercase", color:T.gold }}>PAAS · Orb Sys</p>
          <h1 style={{ margin:0, fontSize:20, fontFamily:T.serif,
            fontWeight:400, color:T.text }}>Sign in</h1>
          <p style={{ margin:"6px 0 0", fontSize:11, color:T.textSub }}>
            Enter your handle or email
          </p>
        </div>

        {[
          { label:"Handle or email", value:identifier, set:setIdentifier, type:"text",    ph:"@handle or email" },
          { label:"Password",        value:password,   set:setPassword,   type:"password", ph:"··········" },
        ].map(({ label, value, set, type, ph }) => (
          <div key={label} style={{ marginBottom:16 }}>
            <p style={{ margin:"0 0 5px", fontSize:9, color:T.muted,
              letterSpacing:2, textTransform:"uppercase" }}>{label}</p>
            <input
              type={type} value={value} placeholder={ph}
              onChange={e => set(e.target.value)}
              onKeyDown={e => e.key === "Enter" && login()}
              style={{
                width:"100%", boxSizing:"border-box",
                padding:"9px 11px",
                background:"#0d0d0d", border:`1px solid ${T.border}`,
                borderRadius:5, color:T.text, fontFamily:T.mono,
                fontSize:12, outline:"none",
              }}
              onFocus={e => e.target.style.borderColor = T.gold}
              onBlur={e => e.target.style.borderColor = T.border}
            />
          </div>
        ))}

        {error && (
          <p style={{ margin:"0 0 12px", fontSize:11, color:"#c87a6e",
            fontFamily:T.mono }}>{error}</p>
        )}

        <button
          onClick={login}
          disabled={loading || !identifier || !password}
          style={{
            width:"100%", padding:"10px",
            background:"transparent",
            border:`1px solid ${T.gold}40`,
            borderRadius:5, color:T.gold,
            fontFamily:T.mono, fontSize:11, cursor:"pointer",
            letterSpacing:2, textTransform:"uppercase",
            opacity: loading || !identifier || !password ? 0.4 : 1,
            transition:"border-color 0.15s",
          }}
          onMouseEnter={e => { if (!loading) (e.target as HTMLElement).style.borderColor = T.gold; }}
          onMouseLeave={e => { (e.target as HTMLElement).style.borderColor = `${T.gold}40`; }}
        >
          {loading ? "Signing in…" : "Sign in →"}
        </button>

        <p style={{ margin:"20px 0 0", fontSize:10, color:T.textDim, textAlign:"center" }}>
          New to Orb Sys?{" "}
          <a href="/auth/register" style={{ color:T.gold, textDecoration:"none" }}>
            Create account
          </a>
          {" or "}
          <a href="/setup" style={{ color:T.gold, textDecoration:"none" }}>
            start an org
          </a>
        </p>
      </div>
    </div>
  );
}
