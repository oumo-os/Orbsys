"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

interface Proposal {
  key: string;
  title: string;
  sequence: number;
  mandatory: boolean;
  cell_exists: boolean;
  cell_state: string | null;
  motion_state: string | null;
  resolved: boolean;
}

interface BootstrapStatus {
  org_id: string;
  template: string;
  phase: "pre_founding_circle" | "founding_deliberation" | "complete";
  verified_members: number;
  founding_circle: {
    formed: boolean;
    member_count: number;
    quorum_min: number;
    quorum_target: number;
  };
  proposals: Proposal[];
  mandatory_proposals_resolved: boolean;
  bootstrap_complete_surfaced: boolean;
}

function StatusDot({ resolved, exists }: { resolved: boolean; exists: boolean }) {
  const color = resolved ? "var(--green, #5a9e6e)"
    : exists   ? "var(--gold)"
    :             "var(--border)";
  return (
    <div style={{
      width: 8, height: 8, borderRadius: "50%",
      background: color, flexShrink: 0, marginTop: 5,
    }} />
  );
}

export default function OnboardPage() {
  const router = useRouter();
  const params = useSearchParams();
  const orgId  = params.get("org");
  const memberId = params.get("member");
  const memberName = params.get("name") ?? "";
  const memberHandle = params.get("handle") ?? "";

  const setOrgSession = useAuthStore((s) => s.setOrgSession);

  const [status,   setStatus]   = useState<BootstrapStatus | null>(null);
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [copied,   setCopied]   = useState(false);

  const enterOrg = useCallback(async () => {
    if (!orgId) return;
    try {
      const { platformApi } = await import("@/lib/api");
      const sessionRes = await platformApi.enterOrg(orgId);
      const st = sessionRes.data;
      setOrgSession({
        id:             memberId ?? st.member_id,
        handle:         memberHandle,
        display_name:   memberName,
        org_id:         st.org_id,
        current_state:  st.state,
      }, st.org_session_token);
      router.replace("/org/commons");
    } catch {
      localStorage.removeItem("orbsys_access_token");
      localStorage.removeItem("orbsys_platform_token");
      localStorage.removeItem("orbsys_refresh_token");
      router.replace("/auth/login");
    }
  }, [orgId, memberId, memberName, memberHandle, setOrgSession, router]);

  const fetchStatus = useCallback(async () => {
    if (!orgId) return;
    try {
      const r = await api.get(`/setup/status/${orgId}`);
      setStatus(r.data);
      if (r.data.phase === "complete") {
        setTimeout(() => enterOrg(), 1500);
      }
    } catch { /* silent — retry on next poll */ }
  }, [orgId, router, enterOrg]);

  useEffect(() => {
    fetchStatus();
    const iv = setInterval(fetchStatus, 8000);
    return () => clearInterval(iv);
  }, [fetchStatus]);

  // Check if bootstrap_complete should surface when mandatory proposals resolve
  useEffect(() => {
    if (!orgId || !status?.mandatory_proposals_resolved) return;
    if (status.bootstrap_complete_surfaced) return;
    api.post(`/setup/check-proposals/${orgId}`).catch(() => {});
  }, [orgId, status]);

  function copyInviteLink() {
    const link = `${window.location.origin}/join/${status?.org_id}`;
    navigator.clipboard.writeText(link).then(() => {
      setCopied(true);
      setInviteLink(link);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  if (!status) return (
    <div style={{ minHeight: "100vh", background: "var(--bg)",
      display: "flex", alignItems: "center", justifyContent: "center" }}>
      <p style={{ fontFamily: "monospace", fontSize: 12, color: "var(--text-muted)" }}>
        Loading…
      </p>
    </div>
  );

  const fc = status.founding_circle;
  const phaseDone = status.phase === "complete";

  return (
    <div style={{
      minHeight: "100vh", background: "var(--bg)",
      color: "var(--text)", padding: "48px 24px",
      display: "flex", flexDirection: "column", alignItems: "center",
    }}>
      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: 40, maxWidth: 560 }}>
        <p style={{ margin: "0 0 6px", fontSize: 10, color: "var(--gold)",
          letterSpacing: 3, textTransform: "uppercase",
          fontFamily: "monospace" }}>
          Bootstrap in progress
        </p>
        <h1 style={{ margin: "0 0 10px", fontSize: 24,
          fontFamily: "var(--font-display,'Lora',serif)", fontWeight: 400 }}>
          {phaseDone
            ? "Governance is live"
            : fc.formed
            ? "Founding circle deliberating"
            : "Waiting for the founding pool"}
        </h1>
        <p style={{ margin: 0, fontSize: 13, color: "var(--text-muted)",
          fontFamily: "var(--font-display,'Lora',serif)", lineHeight: 1.7 }}>
          {phaseDone
            ? "Bootstrap complete — redirecting to your Commons."
            : fc.formed
            ? `The founding circle has ${fc.member_count} member${fc.member_count !== 1 ? "s" : ""} and is working through the founding proposals. All members can participate in the open deliberation Cells.`
            : `The founding circle forms once ${fc.quorum_min}–${fc.quorum_target} members complete credential verification. Invite others to register and submit their W_h credentials.`}
        </p>
      </div>

      <div style={{ width: "100%", maxWidth: 640, display: "flex", flexDirection: "column", gap: 16 }}>

        {/* Phase progress bar */}
        <div style={{ padding: "20px 24px", background: "var(--surface)",
          border: "1px solid var(--border)", borderRadius: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
            {[
              { label: "Registrations",   done: true },
              { label: "Verification",    done: status.verified_members >= fc.quorum_min },
              { label: "Founding circle", done: fc.formed },
              { label: "Deliberation",    done: status.mandatory_proposals_resolved },
              { label: "Live",            done: phaseDone },
            ].map((s, i) => (
              <div key={s.label} style={{ flex: 1, textAlign: "center", position: "relative" }}>
                {i > 0 && (
                  <div style={{
                    position: "absolute", top: 10, left: "-50%", width: "100%",
                    height: 2, background: s.done ? "var(--gold)" : "var(--border)",
                    transition: "background 0.4s",
                  }} />
                )}
                <div style={{
                  width: 22, height: 22, borderRadius: "50%",
                  background: s.done ? "var(--gold-glow)" : "var(--surface-raised)",
                  border: `2px solid ${s.done ? "var(--gold)" : "var(--border)"}`,
                  margin: "0 auto 6px",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  position: "relative", zIndex: 1,
                  transition: "border-color 0.4s",
                }}>
                  {s.done && <span style={{ fontSize: 9, color: "var(--gold)" }}>✓</span>}
                </div>
                <p style={{ margin: 0, fontSize: 9, color: s.done ? "var(--gold)" : "var(--text-dim)",
                  fontFamily: "monospace", textTransform: "uppercase", letterSpacing: 0.5 }}>
                  {s.label}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Member count / invite */}
        {!fc.formed && (
          <div style={{ padding: "20px 24px", background: "var(--surface)",
            border: "1px solid var(--border)", borderRadius: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between",
              alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <p style={{ margin: "0 0 4px", fontSize: 10, color: "var(--text-muted)",
                  fontFamily: "monospace", textTransform: "uppercase", letterSpacing: 1 }}>
                  Verified members
                </p>
                <p style={{ margin: 0, fontSize: 28, fontFamily: "monospace",
                  color: "var(--gold)" }}>
                  {status.verified_members}
                  <span style={{ fontSize: 13, color: "var(--text-muted)",
                    marginLeft: 6 }}>
                    / {fc.quorum_min} min to form
                  </span>
                </p>
              </div>
              <button onClick={copyInviteLink}
                style={{ padding: "8px 16px",
                  background: copied ? "var(--gold-glow)" : "transparent",
                  border: "1px solid var(--border)", borderRadius: 7,
                  color: copied ? "var(--gold)" : "var(--text-muted)",
                  fontFamily: "monospace", fontSize: 10, cursor: "pointer",
                  letterSpacing: 1, transition: "all 0.2s" }}>
                {copied ? "Link copied ✓" : "Copy invite link"}
              </button>
            </div>
            {/* Progress bar */}
            <div style={{ height: 3, background: "var(--border)", borderRadius: 2 }}>
              <div style={{
                height: "100%", borderRadius: 2, background: "var(--gold)",
                width: `${Math.min(100, (status.verified_members / fc.quorum_min) * 100)}%`,
                transition: "width 0.6s ease",
              }} />
            </div>
          </div>
        )}

        {/* Founding proposals */}
        {fc.formed && status.proposals.length > 0 && (
          <div style={{ padding: "20px 24px", background: "var(--surface)",
            border: "1px solid var(--border)", borderRadius: 10 }}>
            <p style={{ margin: "0 0 16px", fontSize: 10, color: "var(--text-muted)",
              fontFamily: "monospace", textTransform: "uppercase", letterSpacing: 1 }}>
              Founding proposals
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {status.proposals
                .filter(p => p.key !== "bootstrap_complete" || p.cell_exists)
                .sort((a, b) => a.sequence - b.sequence)
                .map((p) => (
                  <div key={p.key} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                    <StatusDot resolved={p.resolved} exists={p.cell_exists} />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <p style={{ margin: 0, fontSize: 12,
                          color: p.resolved ? "var(--text-muted)" : "var(--text)",
                          fontFamily: "var(--font-display,'Lora',serif)",
                          textDecoration: p.resolved ? "line-through" : "none" }}>
                          {p.title}
                        </p>
                        {p.mandatory && !p.resolved && (
                          <span style={{ fontSize: 8, padding: "1px 6px",
                            borderRadius: 20, background: "var(--gold-glow)",
                            border: "1px solid var(--gold-dim)",
                            color: "var(--gold)", fontFamily: "monospace",
                            textTransform: "uppercase", letterSpacing: 0.5 }}>
                            required
                          </span>
                        )}
                        {p.key === "bootstrap_complete" && p.cell_exists && !p.resolved && (
                          <span style={{ fontSize: 8, padding: "1px 6px",
                            borderRadius: 20, background: "rgba(90,158,110,0.12)",
                            border: "1px solid rgba(90,158,110,0.3)",
                            color: "var(--green, #5a9e6e)", fontFamily: "monospace",
                            textTransform: "uppercase", letterSpacing: 0.5 }}>
                            ready
                          </span>
                        )}
                      </div>
                      {!p.resolved && p.cell_state && (
                        <p style={{ margin: "2px 0 0", fontSize: 10,
                          color: "var(--text-dim)", fontFamily: "monospace" }}>
                          {p.cell_state === "active" ? "Deliberating" : p.cell_state}
                          {p.motion_state ? ` · motion ${p.motion_state}` : ""}
                        </p>
                      )}
                    </div>
                    {p.cell_exists && !p.resolved && (
                      <button
                        onClick={() => router.push("/org/cells")}
                        style={{ padding: "4px 10px", background: "transparent",
                          border: "1px solid var(--border)", borderRadius: 5,
                          color: "var(--text-dim)", fontFamily: "monospace",
                          fontSize: 9, cursor: "pointer", flexShrink: 0 }}>
                        Open →
                      </button>
                    )}
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Nav to workspace */}
        {fc.formed && (
          <button
            onClick={() => router.push("/org/commons")}
            style={{ padding: "14px",
              background: "var(--gold-glow)",
              border: "1px solid var(--gold-dim)",
              borderRadius: 8, color: "var(--gold)",
              fontFamily: "monospace", fontSize: 11,
              cursor: "pointer", letterSpacing: 1,
              textTransform: "uppercase" }}>
            Go to Commons →
          </button>
        )}

      </div>
    </div>
  );
}
