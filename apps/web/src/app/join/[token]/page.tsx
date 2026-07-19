"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { invitationApi, platformApi, accountApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const T = {
  bg:"#050505", surface:"#080808", border:"#141414",
  gold:"#c8a96e", muted:"#3a3a3a", textDim:"#555555",
  text:"#cccccc", textSub:"#888888",
  mono:"'DM Mono', monospace", serif:"'Lora', serif",
};

interface InvitationDetails {
  invitation_id: string;
  org_id: string;
  org_name: string;
  org_slug: string;
  message: string | null;
  invited_handle: string | null;
  invited_email: string | null;
  status: string;
  expires_at: string | null;
}

type Mode = "loading" | "expired" | "accepted" | "login" | "register" | "pending";

export default function JoinPage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;
  const { setPlatformAuth, setOrgSession } = useAuthStore();

  const [invitation, setInvitation] = useState<InvitationDetails | null>(null);
  const [mode, setMode] = useState<Mode>("loading");
  const [error, setError] = useState<string | null>(null);

  const [handle, setHandle] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [legalName, setLegalName] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    const hasToken = !!localStorage.getItem("orbsys_access_token");
    if (hasToken) {
      invitationApi.get(token)
        .then(res => { setInvitation(res.data); setMode("pending"); })
        .catch(err => {
          const detail = err.response?.data?.detail ?? "";
          if (detail === "INVITATION_EXPIRED" || detail?.startsWith("INVITATION_")) setMode("expired");
          else setMode("expired");
        });
    } else {
      invitationApi.get(token)
        .then(res => { setInvitation(res.data); setMode("register"); })
        .catch(err => {
          const detail = err.response?.data?.detail ?? "";
          if (detail === "INVITATION_EXPIRED" || detail?.startsWith("INVITATION_")) setMode("expired");
          else setMode("expired");
        });
    }
  }, [token]);

  const acceptInvitation = useCallback(async (sessionToken?: string) => {
    setLoading(true); setError(null);
    try {
      const { invitationApi: invApi } = await import("@/lib/api");
      const res = await invApi.accept(token, {
        handle: handle.trim() || invitation?.invited_handle || undefined,
        display_name: handle.trim() || invitation?.invited_handle || undefined,
      });
      const data = res.data;

      const { platformApi: pApi } = await import("@/lib/api");
      const sessionRes = await pApi.enterOrg(data.org_id);
      const st = sessionRes.data;
      setOrgSession({
        id:             data.member_id,
        handle:         handle.trim() || invitation?.invited_handle || "",
        display_name:   handle.trim() || invitation?.invited_handle || "",
        org_id:         data.org_id,
        org_slug:       data.org_slug,
        current_state:  st.state,
      }, st.org_session_token);
      setMode("accepted");
      setTimeout(() => router.replace("/org/commons"), 1500);
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setError(detail ?? "Failed to accept invitation.");
    } finally {
      setLoading(false);
    }
  }, [token, handle, invitation, setOrgSession, router]);

  async function register() {
    if (!handle.trim() || !email.trim() || !password) return;
    setLoading(true); setError(null);
    try {
      const res = await platformApi.register(handle.trim(), email.trim(), password, legalName.trim() || undefined);
      const data = res.data;
      setPlatformAuth(
        { id: data.account_id, handle: handle.trim(), legal_name: legalName.trim() || null },
        data.tokens.access_token,
        data.tokens.refresh_token,
      );
      await acceptInvitation();
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setError(detail ?? "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  async function login() {
    if (!handle.trim() || !password) return;
    setLoading(true); setError(null);
    try {
      const res = await platformApi.login(handle.trim(), password);
      const data = res.data;
      setPlatformAuth(
        data.account,
        data.tokens.access_token,
        data.tokens.refresh_token,
      );
      await acceptInvitation();
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

  if (mode === "loading") {
    return (
      <div style={{ minHeight:"100vh", background:T.bg, display:"flex",
        alignItems:"center", justifyContent:"center", fontFamily:T.mono }}>
        <p style={{ color:T.textSub, fontSize:12 }}>Loading invitation…</p>
      </div>
    );
  }

  if (mode === "expired" || mode === "accepted") {
    return (
      <div style={{ minHeight:"100vh", background:T.bg, display:"flex",
        alignItems:"center", justifyContent:"center", fontFamily:T.mono }}>
        <div style={{ textAlign:"center" }}>
          <p style={{ color: mode === "accepted" ? T.gold : "#c87a6e", fontSize:14, marginBottom:12 }}>
            {mode === "accepted"
              ? "✓ Joining organization…"
              : "This invitation has expired or is no longer valid."}
          </p>
          {mode === "expired" && (
            <a href="/auth/login" style={{ color:T.gold, fontSize:12, textDecoration:"none" }}>
              Go to login →
            </a>
          )}
        </div>
      </div>
    );
  }

  const isRegister = mode === "register";

  return (
    <div style={{
      minHeight:"100vh", background:T.bg, display:"flex",
      alignItems:"center", justifyContent:"center", fontFamily:T.mono,
    }}>
      <div style={{
        width:340, padding:"32px 28px",
        background:T.surface, border:`1px solid ${T.border}`,
        borderRadius:8,
      }}>
        <div style={{ marginBottom:24 }}>
          <p style={{ margin:"0 0 4px", fontSize:11, letterSpacing:4,
            textTransform:"uppercase", color:T.gold }}>Invitation</p>
          <h1 style={{ margin:0, fontSize:18, fontFamily:T.serif,
            fontWeight:400, color:T.text }}>{invitation?.org_name ?? "Organization"}</h1>
          {invitation?.message && (
            <p style={{ margin:"8px 0 0", fontSize:11, color:T.textSub,
              fontStyle:"italic" }}>&ldquo;{invitation.message}&rdquo;</p>
          )}
          {invitation?.invited_handle && (
            <p style={{ margin:"6px 0 0", fontSize:10, color:T.muted }}>
              Invited as: <span style={{color:T.text}}>@{invitation.invited_handle}</span>
            </p>
          )}
        </div>

        {isRegister && (
          <p style={{ margin:"0 0 16px", fontSize:10, color:T.textDim }}>
            Create a platform account to join this organization.
          </p>
        )}
        {!isRegister && (
          <p style={{ margin:"0 0 16px", fontSize:10, color:T.textDim }}>
            Log in to accept this invitation.
          </p>
        )}

        {[
          { label:"Handle",     value:handle,    set:setHandle,    type:"text",     ph: invitation?.invited_handle || "@handle" },
          ...(isRegister ? [
            { label:"Email",    value:email,     set:setEmail,     type:"email",    ph:"you@example.com" },
            { label:"Name",     value:legalName, set:setLegalName, type:"text",     ph:"Optional" },
          ] : []),
          { label:"Password",   value:password,  set:setPassword,  type:"password", ph:"··········" },
        ].map(({ label, value, set, type, ph }) => (
          <div key={label} style={{ marginBottom:14 }}>
            <p style={{ margin:"0 0 5px", fontSize:9, color:T.muted,
              letterSpacing:2, textTransform:"uppercase" }}>{label}</p>
            <input
              type={type} value={value} placeholder={ph}
              onChange={e => set(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter") isRegister ? register() : login();
              }}
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
          onClick={isRegister ? register : login}
          disabled={loading || !handle || !password || (isRegister && !email)}
          style={{
            width:"100%", padding:"10px",
            background:"transparent",
            border:`1px solid ${T.gold}40`,
            borderRadius:5, color:T.gold,
            fontFamily:T.mono, fontSize:11, cursor:"pointer",
            letterSpacing:2, textTransform:"uppercase",
            opacity: loading || !handle || !password || (isRegister && !email) ? 0.4 : 1,
            transition:"border-color 0.15s",
          }}
          onMouseEnter={e => { if (!loading) (e.target as HTMLElement).style.borderColor = T.gold; }}
          onMouseLeave={e => { (e.target as HTMLElement).style.borderColor = `${T.gold}40`; }}
        >
          {loading
            ? (isRegister ? "Creating…" : "Signing in…")
            : (isRegister ? "Register & join →" : "Login & join →")}
        </button>

        <p style={{ margin:"20px 0 0", fontSize:10, color:T.textDim, textAlign:"center" }}>
          {isRegister ? (
            <>Already have an account?{" "}
              <button onClick={() => setMode("login")} style={{
                background:"none", border:"none", color:T.gold,
                fontFamily:T.mono, fontSize:10, cursor:"pointer", padding:0,
              }}>Sign in</button></>
          ) : (
            <>New to Orb Sys?{" "}
              <button onClick={() => setMode("register")} style={{
                background:"none", border:"none", color:T.gold,
                fontFamily:T.mono, fontSize:10, cursor:"pointer", padding:0,
              }}>Create account</button></>
          )}
        </p>
      </div>
    </div>
  );
}
