"use client";

import { useEffect, useState, useCallback, FormEvent } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Eye, EyeOff, CheckCircle, RotateCcw, AlertTriangle, Send, Lock } from "lucide-react";

// Blind review calls the blind API on port 8001 directly with the isolated view token.
// The session JWT is NEVER sent to the blind endpoint.

const BLIND_API = process.env.NEXT_PUBLIC_BLIND_API_URL ?? "http://localhost:8001";

interface Contribution {
  id: string;
  body: string;
  contribution_type: string;
  sequence: number;
  created_at: string;
}

interface MotionContent {
  motion_id: string;
  motion_type: string;
  directive_body: string | null;
  commitments: string[] | null;
  ambiguities_flagged: string[] | null;
  specifications: {
    parameter: string;
    proposed_value: unknown;
    justification: string;
  }[] | null;
}

interface ReviewContent {
  stf_instance_id: string;
  assignment_id: string;
  stf_type: string;
  mandate: string;
  contributions: Contribution[];
  motion: MotionContent | null;
  deadline: string | null;
  verdict_filed_at: string | null;
}

const VERDICT_OPTIONS: { value: string; label: string; colour: string; desc: string }[] = [
  { value: "approve",           label: "Approve",          colour: "text-emerald-400", desc: "Decision is sound — advance to implementation" },
  { value: "revision_request",  label: "Revision request", colour: "text-amber-400",   desc: "Return with specific directive attached" },
  { value: "reject",            label: "Reject",           colour: "text-red-400",     desc: "Motion is not appropriate — dissolve with report" },
];

async function fetchContent(stfId: string, token: string): Promise<ReviewContent> {
  const res = await fetch(`${BLIND_API}/blind/${stfId}/content`, {
    headers: { "X-Isolated-View-Token": token },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

async function fileVerdict(
  stfId: string,
  token: string,
  payload: { verdict: string; rationale?: string; revision_directive?: string }
): Promise<{ verdict_id: string; verdict: string; filed_at: string }> {
  const res = await fetch(`${BLIND_API}/blind/${stfId}/verdicts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Isolated-View-Token": token,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export default function BlindReviewPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();

  // Token comes from URL param ?token=... (set when assignment is created)
  const [token, setToken] = useState(searchParams.get("token") ?? "");
  const [tokenInput, setTokenInput] = useState("");
  const [showToken, setShowToken] = useState(false);

  const [content, setContent] = useState<ReviewContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  const [verdict, setVerdict] = useState("");
  const [rationale, setRationale] = useState("");
  const [directive, setDirective] = useState("");
  const [filing, setFiling] = useState(false);
  const [filed, setFiled] = useState(false);
  const [fileErr, setFileErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setLoadErr(null);
    try {
      const data = await fetchContent(id, token);
      setContent(data);
      if (data.verdict_filed_at) setFiled(true);
    } catch (e: unknown) {
      setLoadErr((e as Error).message ?? "Failed to load review content");
    } finally { setLoading(false); }
  }, [id, token]);

  useEffect(() => { if (token) load(); }, [token, load]);

  function handleTokenSubmit(e: FormEvent) {
    e.preventDefault();
    setToken(tokenInput.trim());
  }

  async function handleFileVerdict(e: FormEvent) {
    e.preventDefault();
    if (!verdict) return;
    setFiling(true); setFileErr(null);
    try {
      await fileVerdict(id, token, {
        verdict,
        rationale: rationale || undefined,
        revision_directive: verdict === "revision_request" ? directive : undefined,
      });
      setFiled(true);
    } catch (ex: unknown) {
      setFileErr((ex as Error).message ?? "Filing failed");
    } finally { setFiling(false); }
  }

  // ── Token entry screen ────────────────────────────────────────────────────

  if (!token) return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="card p-8 w-full max-w-sm">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-[var(--stf-astf)]/15 border
            border-[var(--stf-astf)]/40 flex items-center justify-center">
            <Lock size={18} style={{ color: "var(--stf-astf)" }} />
          </div>
          <div>
            <h1 className="font-display text-base text-[var(--text)]">Blind Review</h1>
            <p className="text-xs font-mono text-[var(--text-muted)]">
              Isolated review endpoint
            </p>
          </div>
        </div>

        <div className="p-3 rounded bg-[var(--gold-glow)] border border-[var(--gold)]/20 mb-5">
          <p className="text-[10px] font-mono text-[var(--gold)] leading-relaxed">
            This endpoint accepts only your isolated view token.
            Your session credentials are not sent here — reviewer identity remains sealed
            until the full panel has filed.
          </p>
        </div>

        <form onSubmit={handleTokenSubmit} className="space-y-3">
          <div>
            <label className="section-label block mb-1.5">Isolated view token</label>
            <div className="relative">
              <input
                type={showToken ? "text" : "password"}
                value={tokenInput}
                onChange={e => setTokenInput(e.target.value)}
                placeholder="eyJ…"
                required
                className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                  px-3 py-2 text-sm font-mono text-[var(--text)] pr-9
                  focus:outline-none focus:border-[var(--gold)]"
              />
              <button type="button" onClick={() => setShowToken(!showToken)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2
                  text-[var(--text-muted)] hover:text-[var(--text)]">
                {showToken ? <EyeOff size={13} /> : <Eye size={13} />}
              </button>
            </div>
          </div>
          <button type="submit" className="btn btn-primary w-full text-xs">
            Access review
          </button>
        </form>
      </div>
    </div>
  );

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) return (
    <div className="space-y-4">
      {[1, 2, 3].map(i => (
        <div key={i} className="card p-5 animate-pulse">
          <div className="h-3 bg-[var(--surface-raised)] rounded w-1/2 mb-3" />
          <div className="h-2 bg-[var(--surface-raised)] rounded w-full mb-1.5" />
          <div className="h-2 bg-[var(--surface-raised)] rounded w-3/4" />
        </div>
      ))}
    </div>
  );

  // ── Load error ────────────────────────────────────────────────────────────

  if (loadErr) return (
    <div className="text-center py-16">
      <AlertTriangle size={28} className="mx-auto mb-3 text-red-400" />
      <p className="text-sm font-mono text-red-400 mb-1">Access denied</p>
      <p className="text-xs text-[var(--text-muted)] mb-4">{loadErr}</p>
      <button onClick={() => { setToken(""); setTokenInput(""); }}
        className="btn btn-ghost text-xs gap-1.5">
        <RotateCcw size={11} /> Try different token
      </button>
    </div>
  );

  if (!content) return null;

  // ── Already filed ─────────────────────────────────────────────────────────

  if (filed) return (
    <div className="text-center py-16">
      <CheckCircle size={32} className="mx-auto mb-3 text-emerald-400" />
      <h2 className="font-display text-lg text-[var(--text)] mb-1">Verdict filed</h2>
      <p className="text-sm text-[var(--text-muted)]">
        Your verdict has been recorded. Identity remains sealed until the panel closes.
      </p>
    </div>
  );

  // ── Review interface ──────────────────────────────────────────────────────

  return (
    <div className="space-y-5 max-w-2xl mx-auto">
      {/* Blind review header */}
      <div className="card p-5 border-[var(--stf-astf)]/30">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-lg bg-[var(--stf-astf)]/15 border
            border-[var(--stf-astf)]/40 flex items-center justify-center">
            <Lock size={15} style={{ color: "var(--stf-astf)" }} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono uppercase tracking-wider"
                style={{ color: "var(--stf-astf)" }}>
                {content.stf_type.toUpperCase()}
              </span>
              <span className="text-[10px] font-mono text-[var(--text-dim)]">
                Blind review — identity sealed
              </span>
            </div>
            {content.deadline && (
              <p className={`text-[10px] font-mono mt-0.5 ${
                new Date(content.deadline) < new Date()
                  ? "text-red-400" : "text-[var(--text-muted)]"
              }`}>
                Deadline: {new Date(content.deadline).toLocaleDateString("en-GB", {
                  day: "numeric", month: "short", year: "numeric",
                })}
              </p>
            )}
          </div>
        </div>
        <p className="text-sm text-[var(--text)] leading-relaxed">{content.mandate}</p>
      </div>

      {/* Motion content */}
      {content.motion && (
        <div className="card p-5">
          <p className="section-label mb-3">
            Motion — {content.motion.motion_type.replace("_", "-")}
          </p>

          {content.motion.directive_body && (
            <div className="mb-4">
              <p className="text-[10px] font-mono text-[var(--text-dim)] uppercase
                tracking-wider mb-2">Directive</p>
              <p className="text-sm text-[var(--text)] leading-relaxed whitespace-pre-wrap font-body">
                {content.motion.directive_body}
              </p>
            </div>
          )}

          {content.motion.commitments && content.motion.commitments.length > 0 && (
            <div className="mb-4">
              <p className="text-[10px] font-mono text-[var(--text-dim)] uppercase
                tracking-wider mb-2">Commitments</p>
              <ul className="space-y-1.5">
                {content.motion.commitments.map((c, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <span className="text-[var(--gold)] shrink-0 mt-0.5">◎</span>
                    <span className="text-[var(--text)]">{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {content.motion.specifications && content.motion.specifications.length > 0 && (
            <div>
              <p className="text-[10px] font-mono text-[var(--text-dim)] uppercase
                tracking-wider mb-2">Specifications</p>
              <div className="space-y-2">
                {content.motion.specifications.map((s, i) => (
                  <div key={i} className="p-3 rounded bg-[var(--surface-raised)]
                    border border-[var(--border)]">
                    <code className="text-xs font-mono text-[var(--gold)]">{s.parameter}</code>
                    <div className="text-xs font-mono text-[var(--text)] mt-1">
                      → {JSON.stringify(s.proposed_value)}
                    </div>
                    <p className="text-xs text-[var(--text-muted)] mt-1">{s.justification}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Deliberation record */}
      {content.contributions.length > 0 && (
        <div className="card p-5">
          <p className="section-label mb-3">
            Deliberation record ({content.contributions.length} contributions)
          </p>
          <div className="space-y-4 max-h-80 overflow-y-auto pr-1">
            {content.contributions.map(c => (
              <div key={c.id} className="border-l-2 border-[var(--border)] pl-4 py-1">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[10px] font-mono text-[var(--text-dim)]">
                    #{c.sequence}
                  </span>
                  {c.contribution_type !== "discussion" && (
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded
                      bg-[var(--blue-dim)] text-[var(--blue)] border border-[var(--blue)]/20">
                      {c.contribution_type}
                    </span>
                  )}
                  <span className="text-[10px] font-mono text-[var(--text-dim)]">
                    {new Date(c.created_at).toLocaleDateString("en-GB", {
                      day: "numeric", month: "short",
                    })}
                  </span>
                </div>
                <p className="text-sm text-[var(--text)] leading-relaxed whitespace-pre-wrap font-body">
                  {c.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Verdict form */}
      <div className="card p-6">
        <p className="section-label mb-4">File verdict</p>
        <form onSubmit={handleFileVerdict} className="space-y-5">
          {/* Verdict choice */}
          <div className="space-y-2">
            {VERDICT_OPTIONS.map(opt => (
              <label key={opt.value}
                className={`flex items-start gap-3 p-3 rounded border cursor-pointer
                  transition-all ${
                  verdict === opt.value
                    ? "border-current/40 bg-current/10"
                    : "border-[var(--border)] hover:border-[var(--border)]"
                } ${opt.colour}`}>
                <input type="radio" name="verdict" value={opt.value}
                  checked={verdict === opt.value}
                  onChange={() => setVerdict(opt.value)}
                  className="mt-0.5 accent-current shrink-0" />
                <div>
                  <p className="text-sm font-mono font-medium">{opt.label}</p>
                  <p className="text-[11px] text-[var(--text-muted)] mt-0.5 font-body">
                    {opt.desc}
                  </p>
                </div>
              </label>
            ))}
          </div>

          {/* Rationale */}
          <div>
            <label className="section-label block mb-1.5">
              Rationale <span className="text-[var(--text-dim)] normal-case">(recommended)</span>
            </label>
            <textarea value={rationale} onChange={e => setRationale(e.target.value)}
              rows={4} placeholder="Evidence quality, process soundness, ethical considerations…"
              className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                px-3 py-2 text-sm font-body text-[var(--text)] resize-none
                focus:outline-none focus:border-[var(--gold)]
                placeholder:text-[var(--text-dim)]" />
          </div>

          {/* Revision directive (required for revision_request) */}
          {verdict === "revision_request" && (
            <div>
              <label className="section-label block mb-1.5">
                Revision directive <span className="text-red-400">*</span>
              </label>
              <textarea value={directive} onChange={e => setDirective(e.target.value)}
                rows={4} required placeholder="Specific instruction for the Cell to address…"
                className="w-full bg-[var(--surface)] border border-amber-800/40 rounded
                  px-3 py-2 text-sm font-body text-[var(--text)] resize-none
                  focus:outline-none focus:border-amber-500
                  placeholder:text-[var(--text-dim)]" />
            </div>
          )}

          {fileErr && (
            <div className="text-xs font-mono text-red-400 bg-[var(--red-dim)]
              border border-red-800/40 rounded px-3 py-2">
              {fileErr}
            </div>
          )}

          <div className="pt-2 border-t border-[var(--border)]">
            <p className="text-[10px] font-mono text-[var(--text-dim)] mb-3">
              Your verdict is recorded without identity. The reviewer pool is revealed only
              on malpractice finding or judicial penalty.
            </p>
            <button type="submit"
              disabled={filing || !verdict ||
                (verdict === "revision_request" && !directive.trim())}
              className="btn btn-primary w-full text-xs gap-1.5 disabled:opacity-40">
              <Send size={11} />
              {filing ? "Filing verdict…" : "File verdict"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
