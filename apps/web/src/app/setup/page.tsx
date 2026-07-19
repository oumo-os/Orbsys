"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

interface TemplateCard {
  key: string;
  label: string;
  tagline: string;
  description: string;
  icon: string;
  parameter_highlights: Record<string, unknown>;
  founding_proposal_count: number;
}

interface TemplateList {
  primary: TemplateCard[];
  extended: TemplateCard[];
}

type Step = "select" | "size" | "register" | "creating";

const SIZE_MARKS = [
  { value: 5,    label: "5",    tier: "Micro" },
  { value: 15,   label: "15",   tier: "Small" },
  { value: 50,   label: "50",   tier: "Medium" },
  { value: 150,  label: "150",  tier: "Large" },
  { value: 500,  label: "500+", tier: "Very Large" },
];

function quorumPreview(size: number): { min: number; target: number } {
  if (size <= 15)  return { min: Math.max(3, Math.round(size * 0.4 * 0.6)),  target: Math.min(13, Math.max(3, Math.round(size * 0.4)))  };
  if (size <= 50)  return { min: Math.max(3, Math.round(size * 0.3 * 0.6)),  target: Math.min(13, Math.max(3, Math.round(size * 0.3)))  };
  if (size <= 200) return { min: Math.max(3, Math.round(size * 0.2 * 0.6)),  target: Math.min(13, Math.max(3, Math.round(size * 0.2)))  };
  return              { min: Math.max(3, Math.round(size * 0.1 * 0.6)),       target: Math.min(13, Math.max(3, Math.round(size * 0.1)))  };
}

export default function SetupPage() {
  const router = useRouter();
  const setPlatformAuth = useAuthStore((s) => s.setPlatformAuth);
  const setOrgSession = useAuthStore((s) => s.setOrgSession);

  const [step, setStep]           = useState<Step>("select");
  const [templates, setTemplates] = useState<TemplateList | null>(null);
  const [showExtended, setShowExtended] = useState(false);
  const [selected, setSelected]   = useState<TemplateCard | null>(null);
  const [orgSize, setOrgSize]     = useState(30);

  const [handle,      setHandle]      = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email,       setEmail]       = useState("");
  const [password,    setPassword]    = useState("");
  const [error,       setError]       = useState<string | null>(null);
  const [creating,    setCreating]    = useState(false);

  useEffect(() => {
    api.get("/setup/templates").then((r) => setTemplates(r.data)).catch(() => {});
  }, []);

  async function create() {
    if (!selected || !handle || !displayName || !email || !password) {
      setError("All fields are required.");
      return;
    }
    setCreating(true);
    setStep("creating");
    setError(null);
    try {
      const r = await api.post("/setup/create", {
        template_key:  selected.key,
        org_size:      orgSize,
        handle,
        display_name:  displayName,
        email,
        password,
      });
      const data = r.data;
      setPlatformAuth(
        { id: data.platform_account_id, handle, legal_name: null },
        data.tokens.access_token,
        data.tokens.refresh_token,
      );
      router.push(`/setup/onboard?org=${data.org_id}&member=${data.member_id}&name=${encodeURIComponent(displayName)}&handle=${encodeURIComponent(handle)}`);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Creation failed — check the console.";
      setError(msg);
      setStep("register");
    } finally {
      setCreating(false);
    }
  }

  const visibleTemplates = [
    ...(templates?.primary ?? []),
    ...(showExtended ? (templates?.extended ?? []) : []),
  ];

  const qp = quorumPreview(orgSize);

  return (
    <div style={{
      minHeight: "100vh",
      background: "var(--bg)",
      color: "var(--text)",
      fontFamily: "var(--font-mono, 'DM Mono', monospace)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "48px 24px",
    }}>
      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: 48 }}>
        <p style={{ margin: "0 0 6px", fontSize: 11, letterSpacing: 4,
          textTransform: "uppercase", color: "var(--gold)", opacity: 0.7 }}>
          PAAS · Orb Sys
        </p>
        <h1 style={{ margin: 0, fontSize: 28, fontFamily: "var(--font-display, 'Lora', serif)",
          fontWeight: 400, color: "var(--text)" }}>
          {step === "select"   && "What kind of organisation is this?"}
          {step === "size"     && `Setting up a ${selected?.label ?? ""}`}
          {step === "register" && "Create your account"}
          {step === "creating" && "Building your org…"}
        </h1>
        {step === "select" && (
          <p style={{ margin: "10px 0 0", fontSize: 13, color: "var(--text-muted)",
            fontFamily: "var(--font-display, 'Lora', serif)", maxWidth: 520, lineHeight: 1.7 }}>
            Choose the governance archetype closest to your organisation.
            The founding circle will refine everything — this is a starting point.
          </p>
        )}
      </div>

      {/* Step indicator */}
      <div style={{ display: "flex", gap: 8, marginBottom: 40 }}>
        {(["select","size","register"] as Step[]).map((s, i) => (
          <div key={s} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              width: 24, height: 24, borderRadius: "50%",
              border: `1px solid ${step === s ? "var(--gold)" : "var(--border)"}`,
              background: step === s ? "var(--gold-glow)" : "transparent",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 10, color: step === s ? "var(--gold)" : "var(--text-dim)",
            }}>{i + 1}</div>
            {i < 2 && <div style={{ width: 32, height: 1, background: "var(--border)" }} />}
          </div>
        ))}
      </div>

      {/* ── Step 1: Template selector ── */}
      {step === "select" && (
        <div style={{ width: "100%", maxWidth: 860 }}>
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
            gap: 14, marginBottom: 20,
          }}>
            {visibleTemplates.map((t) => (
              <button
                key={t.key}
                onClick={() => { setSelected(t); setStep("size"); }}
                style={{
                  padding: "20px 20px 18px",
                  background: "var(--surface)",
                  border: `1px solid ${selected?.key === t.key ? "var(--gold)" : "var(--border)"}`,
                  borderRadius: 10, cursor: "pointer", textAlign: "left",
                  transition: "border-color 0.15s, background 0.15s",
                }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--gold-dim)")}
                onMouseLeave={e => (e.currentTarget.style.borderColor =
                  selected?.key === t.key ? "var(--gold)" : "var(--border)")}
              >
                <div style={{ fontSize: 22, marginBottom: 10 }}>{t.icon}</div>
                <p style={{ margin: "0 0 4px", fontSize: 13, color: "var(--text)",
                  fontFamily: "var(--font-display,'Lora',serif)", fontWeight: 500 }}>
                  {t.label}
                </p>
                <p style={{ margin: "0 0 12px", fontSize: 11, color: "var(--gold)",
                  letterSpacing: 0.2, lineHeight: 1.5 }}>
                  {t.tagline}
                </p>
                <p style={{ margin: 0, fontSize: 11, color: "var(--text-muted)",
                  lineHeight: 1.65 }}>
                  {t.description}
                </p>
                <div style={{ marginTop: 14, paddingTop: 12,
                  borderTop: "1px solid var(--border)",
                  display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {Object.entries(t.parameter_highlights).map(([k, v]) => (
                    <span key={k} style={{
                      fontSize: 9, fontFamily: "monospace", padding: "2px 7px",
                      borderRadius: 20, background: "var(--surface-raised)",
                      color: "var(--text-muted)", border: "1px solid var(--border)",
                    }}>
                      {k.replace(/_pct|_policy/, "").replace(/_/g, " ")}={String(v)}
                    </span>
                  ))}
                </div>
              </button>
            ))}
          </div>

          <div style={{ textAlign: "center" }}>
            <button
              onClick={() => setShowExtended((p) => !p)}
              style={{ background: "transparent", border: "none",
                color: "var(--text-dim)", fontSize: 11, cursor: "pointer",
                fontFamily: "monospace", letterSpacing: 1,
                textTransform: "uppercase", padding: "8px 16px" }}
            >
              {showExtended ? "▲ Show fewer" : "▼ More templates"}
            </button>
          </div>
        </div>
      )}

      {/* ── Step 2: Org size ── */}
      {step === "size" && selected && (
        <div style={{ width: "100%", maxWidth: 480 }}>
          <div style={{ padding: "28px", background: "var(--surface)",
            border: "1px solid var(--border)", borderRadius: 12, marginBottom: 24 }}>
            <p style={{ margin: "0 0 6px", fontSize: 10, color: "var(--gold)",
              letterSpacing: 2, textTransform: "uppercase" }}>Selected</p>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
              <span style={{ fontSize: 20 }}>{selected.icon}</span>
              <div>
                <p style={{ margin: 0, fontSize: 15,
                  fontFamily: "var(--font-display,'Lora',serif)", color: "var(--text)" }}>
                  {selected.label}
                </p>
                <p style={{ margin: 0, fontSize: 11, color: "var(--text-muted)" }}>
                  {selected.tagline}
                </p>
              </div>
            </div>

            <p style={{ margin: "0 0 18px", fontSize: 12, color: "var(--text-muted)",
              fontFamily: "var(--font-display,'Lora',serif)", lineHeight: 1.65 }}>
              About how many members do you expect at launch?
              This tunes the founding circle size — it can be changed later.
            </p>

            {/* Slider */}
            <div style={{ marginBottom: 20 }}>
              <input
                type="range" min={3} max={500}
                value={orgSize}
                onChange={e => setOrgSize(Number(e.target.value))}
                style={{ width: "100%", accentColor: "var(--gold)" }}
              />
              <div style={{ display: "flex", justifyContent: "space-between",
                marginTop: 6 }}>
                {SIZE_MARKS.map((m) => (
                  <span key={m.value} style={{ fontSize: 9, color: "var(--text-dim)",
                    fontFamily: "monospace" }}>{m.label}</span>
                ))}
              </div>
            </div>

            {/* Preview */}
            <div style={{ padding: "14px", background: "var(--surface-raised)",
              borderRadius: 8, border: "1px solid var(--border)" }}>
              <p style={{ margin: "0 0 8px", fontSize: 10, color: "var(--text-muted)",
                fontFamily: "monospace", textTransform: "uppercase", letterSpacing: 1 }}>
                Founding circle preview
              </p>
              <div style={{ display: "flex", gap: 24 }}>
                {[
                  ["Org size estimate", orgSize],
                  ["FC forms when", `${qp.min}+ verified`],
                  ["Target size", `${qp.target} members`],
                  ["Proposals", selected.founding_proposal_count],
                ].map(([label, value]) => (
                  <div key={String(label)}>
                    <p style={{ margin: "0 0 2px", fontSize: 9, color: "var(--text-dim)",
                      fontFamily: "monospace", textTransform: "uppercase" }}>{label}</p>
                    <p style={{ margin: 0, fontSize: 16, color: "var(--gold)",
                      fontFamily: "monospace" }}>{value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={() => setStep("select")}
              style={{ flex: 1, padding: "12px", background: "transparent",
                border: "1px solid var(--border)", borderRadius: 8,
                color: "var(--text-muted)", fontFamily: "monospace",
                fontSize: 11, cursor: "pointer" }}>
              ← Back
            </button>
            <button onClick={() => setStep("register")}
              style={{ flex: 2, padding: "12px",
                background: "var(--gold-glow)",
                border: "1px solid var(--gold)",
                borderRadius: 8, color: "var(--gold)",
                fontFamily: "monospace", fontSize: 11,
                cursor: "pointer", letterSpacing: 1,
                textTransform: "uppercase" }}>
              Continue →
            </button>
          </div>
        </div>
      )}

      {/* ── Step 3: Register first member ── */}
      {step === "register" && selected && (
        <div style={{ width: "100%", maxWidth: 440 }}>
          <div style={{ padding: "28px", background: "var(--surface)",
            border: "1px solid var(--border)", borderRadius: 12, marginBottom: 20 }}>
            <p style={{ margin: "0 0 18px", fontSize: 12, color: "var(--text-muted)",
              fontFamily: "var(--font-display,'Lora',serif)", lineHeight: 1.7 }}>
              You're the first member of this organisation. Once enough members
              register and verify credentials, the founding circle will form
              automatically and your governance workspace will open.
            </p>

            {[
              { label: "Handle",       value: handle,      set: setHandle,      type: "text",     ph: "your-handle" },
              { label: "Display name", value: displayName, set: setDisplayName, type: "text",     ph: "Your Name" },
              { label: "Email",        value: email,       set: setEmail,       type: "email",    ph: "you@example.com" },
              { label: "Password",     value: password,    set: setPassword,    type: "password", ph: "··········" },
            ].map(({ label, value, set, type, ph }) => (
              <div key={label} style={{ marginBottom: 16 }}>
                <p style={{ margin: "0 0 6px", fontSize: 10, color: "var(--text-muted)",
                  fontFamily: "monospace", textTransform: "uppercase", letterSpacing: 1 }}>
                  {label}
                </p>
                <input
                  type={type} value={value} placeholder={ph}
                  onChange={e => set(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && create()}
                  style={{
                    width: "100%", boxSizing: "border-box",
                    padding: "10px 12px",
                    background: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                    borderRadius: 7, color: "var(--text)",
                    fontFamily: "var(--font-display,'Lora',serif)",
                    fontSize: 13, outline: "none",
                  }}
                />
              </div>
            ))}

            {error && (
              <p style={{ margin: "8px 0 0", fontSize: 11, color: "#e05050",
                fontFamily: "monospace" }}>{error}</p>
            )}
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={() => setStep("size")}
              style={{ flex: 1, padding: "12px", background: "transparent",
                border: "1px solid var(--border)", borderRadius: 8,
                color: "var(--text-muted)", fontFamily: "monospace",
                fontSize: 11, cursor: "pointer" }}>
              ← Back
            </button>
            <button
              onClick={create}
              disabled={creating || !handle || !displayName || !email || !password}
              style={{ flex: 2, padding: "12px",
                background: "var(--gold-glow)",
                border: "1px solid var(--gold)",
                borderRadius: 8, color: "var(--gold)",
                fontFamily: "monospace", fontSize: 11, cursor: "pointer",
                letterSpacing: 1, textTransform: "uppercase",
                opacity: (creating || !handle || !displayName || !email || !password)
                  ? 0.45 : 1,
              }}>
              {creating ? "Creating…" : "Create organisation →"}
            </button>
          </div>
        </div>
      )}

      {/* ── Creating spinner ── */}
      {step === "creating" && (
        <div style={{ textAlign: "center", padding: 48 }}>
          <div style={{ width: 40, height: 40, borderRadius: "50%",
            border: "2px solid var(--border)",
            borderTopColor: "var(--gold)",
            margin: "0 auto 20px",
            animation: "spin 1s linear infinite" }} />
          <p style={{ fontSize: 13, color: "var(--text-muted)",
            fontFamily: "var(--font-display,'Lora',serif)" }}>
            Seeding your governance workspace…
          </p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}
    </div>
  );
}
