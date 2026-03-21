"use client";

import { useEffect, useState, useCallback, FormEvent } from "react";
import { competenceApi } from "@/lib/api";
import { CheckCircle, Clock, AlertCircle } from "lucide-react";

interface Dormain { id: string; name: string; description: string | null }

interface CompetenceScore {
  dormain_id: string;
  dormain_name: string;
  w_s: number;
  w_h: number;
  w_eff: number;
  mcmp_status: string;
  last_activity_at: string | null;
}

interface LeaderboardEntry {
  rank: number;
  member_id: string;
  handle: string;
  display_name: string;
  w_s: number;
  w_h: number;
}

interface WhClaim {
  id: string;
  dormain_id: string;
  dormain_name: string;
  credential_type: string;
  claimed_value_wh: number;
  status: string;
  verified_at: string | null;
  expires_at: string | null;
}

const CREDENTIAL_TYPES = [
  { value: "degree",                label: "Academic degree" },
  { value: "certification",         label: "Professional certification" },
  { value: "patent",                label: "Patent" },
  { value: "license",               label: "Licence" },
  { value: "verified_contribution", label: "Verified contribution" },
];

const CLAIM_STATUS_STYLE: Record<string, string> = {
  wh_preliminary: "text-amber-400 border-amber-800/40 bg-amber-900/20",
  wh_verified:    "text-emerald-400 border-emerald-800/40 bg-emerald-900/20",
  vstf_pending:   "text-blue-400 border-blue-800/40 bg-blue-900/20",
  rejected:       "text-red-400 border-red-800/40 bg-red-900/20",
};

const MCMP_STYLE: Record<string, string> = {
  active:      "text-emerald-400",
  frozen:      "text-red-400",
  suspended:   "text-red-400",
  under_review:"text-amber-400",
};

// ── W_h Claim Modal ───────────────────────────────────────────────────────────
function WhClaimModal({ dormains, onClose, onSuccess }: {
  dormains: Dormain[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [dormainId, setDormainId]       = useState("");
  const [credentialType, setCredType]   = useState("certification");
  const [claimedValue, setClaimedValue] = useState("1200");
  const [vdcRef, setVdcRef]             = useState("");
  const [justification, setJustification] = useState("");
  const [submitting, setSubmitting]     = useState(false);
  const [err, setErr]                   = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!dormainId) return;
    setSubmitting(true); setErr(null);
    try {
      await competenceApi.submitWhClaim({
        dormain_id: dormainId,
        credential_type: credentialType,
        claimed_value_wh: parseFloat(claimedValue),
        vdc_reference: vdcRef,
        justification,
      });
      onSuccess();
    } catch (ex: unknown) {
      setErr(
        (ex as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? "Submission failed"
      );
    } finally { setSubmitting(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="card w-full max-w-md my-auto">
        <div className="p-5 border-b border-[var(--border)] flex items-center justify-between">
          <div>
            <h2 className="font-display text-base text-[var(--text)]">Submit W_h claim</h2>
            <p className="text-xs font-mono text-[var(--text-muted)] mt-0.5">
              Hard competence credential for vSTF verification
            </p>
          </div>
          <button onClick={onClose}
            className="text-[var(--text-muted)] hover:text-[var(--text)] text-xl leading-none">
            ×
          </button>
        </div>

        <form onSubmit={submit} className="p-5 space-y-4">
          {/* Dormain */}
          <div>
            <label className="section-label block mb-1.5">Dormain</label>
            <select value={dormainId} onChange={e => setDormainId(e.target.value)} required
              className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                px-3 py-2 text-sm font-mono text-[var(--text)]
                focus:outline-none focus:border-[var(--gold)]">
              <option value="">Select dormain…</option>
              {dormains.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>

          {/* Credential type */}
          <div>
            <label className="section-label block mb-1.5">Credential type</label>
            <select value={credentialType} onChange={e => setCredType(e.target.value)}
              className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                px-3 py-2 text-sm font-mono text-[var(--text)]
                focus:outline-none focus:border-[var(--gold)]">
              {CREDENTIAL_TYPES.map(c => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          {/* Claimed W_h value */}
          <div>
            <label className="section-label block mb-1.5">
              Claimed W_h value
              <span className="text-[var(--text-dim)] normal-case ml-1">(0 – 3000)</span>
            </label>
            <input type="number" min="0" max="3000" step="1"
              value={claimedValue} onChange={e => setClaimedValue(e.target.value)} required
              className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                px-3 py-2 text-sm font-mono text-[var(--text)]
                focus:outline-none focus:border-[var(--gold)]" />
            <p className="text-[10px] font-mono text-[var(--text-dim)] mt-1">
              Typical values: Certification ~800–1400 · Degree ~1200–1800 · PhD ~1800–2400
            </p>
          </div>

          {/* VDC reference */}
          <div>
            <label className="section-label block mb-1.5">
              Credential reference (URL or document identifier)
            </label>
            <input type="text" value={vdcRef} onChange={e => setVdcRef(e.target.value)}
              placeholder="https://… or certificate registry ID" required
              className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                px-3 py-2 text-sm font-mono text-[var(--text)]
                placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--gold)]" />
          </div>

          {/* Justification */}
          <div>
            <label className="section-label block mb-1.5">
              Justification
              <span className="text-[var(--text-dim)] normal-case ml-1">(min. 50 characters)</span>
            </label>
            <textarea value={justification} onChange={e => setJustification(e.target.value)}
              rows={4} required minLength={50}
              placeholder="Describe the credential, issuing body, relevance to the dormain, and any verification steps the vSTF can follow…"
              className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                px-3 py-2 text-sm font-body text-[var(--text)] resize-none
                placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--gold)]" />
            <p className="text-[10px] font-mono mt-1 text-right"
              style={{ color: justification.length < 50 ? "var(--red)" : "var(--text-dim)" }}>
              {justification.length} / 50 min
            </p>
          </div>

          {err && (
            <div className="text-xs font-mono text-red-400 bg-[var(--red-dim)]
              border border-red-800/40 rounded px-3 py-2">{err}</div>
          )}

          <div className="pt-2 border-t border-[var(--border)]">
            <p className="text-[10px] font-mono text-[var(--text-dim)] mb-3">
              A vSTF will be commissioned to verify this claim. Your W_s in this dormain
              will be boosted to the verified W_h value on approval.
            </p>
            <div className="flex gap-3">
              <button type="button" onClick={onClose} className="btn btn-ghost flex-1 text-xs">
                Cancel
              </button>
              <button type="submit"
                disabled={submitting || justification.length < 50}
                className="btn btn-primary flex-1 text-xs disabled:opacity-40">
                {submitting ? "Submitting…" : "Submit claim"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function CompetencePage() {
  const [scores, setScores]           = useState<CompetenceScore[]>([]);
  const [dormains, setDormains]       = useState<Dormain[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [claims, setClaims]           = useState<WhClaim[]>([]);
  const [loading, setLoading]         = useState(true);
  const [selectedDormain, setSelectedDormain] = useState<string>("");
  const [showClaimModal, setShowClaimModal]   = useState(false);
  const [tab, setTab] = useState<"scores" | "leaderboard" | "claims">("scores");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [scoresRes, dormainsRes, claimsRes] = await Promise.all([
        competenceApi.myScores(),
        competenceApi.dormains(),
        competenceApi.myWhClaims().catch(() => ({ data: [] })),
      ]);
      const s = scoresRes.data as CompetenceScore[] | { items?: CompetenceScore[] };
      setScores(Array.isArray(s) ? s : (s.items ?? []));
      const d = dormainsRes.data as Dormain[] | { items?: Dormain[] };
      const dArr = Array.isArray(d) ? d : (d.items ?? []);
      setDormains(dArr);
      if (!selectedDormain && dArr.length > 0) setSelectedDormain(dArr[0].id);
      const c = claimsRes.data as WhClaim[] | { items?: WhClaim[] };
      setClaims(Array.isArray(c) ? c : (c.items ?? []));
    } catch { } finally { setLoading(false); }
  }, [selectedDormain]);

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selectedDormain || tab !== "leaderboard") return;
    competenceApi.leaderboard(selectedDormain, { page: 1 })
      .then(r => {
        const data = r.data as LeaderboardEntry[] | { items?: LeaderboardEntry[] };
        setLeaderboard(Array.isArray(data) ? data : (data.items ?? []));
      })
      .catch(() => setLeaderboard([]));
  }, [selectedDormain, tab]);

  if (loading) return (
    <div className="space-y-4">
      {[1, 2, 3].map(i => (
        <div key={i} className="card p-5 animate-pulse">
          <div className="h-3 bg-[var(--surface-raised)] rounded w-1/3 mb-2" />
          <div className="h-2 bg-[var(--surface-raised)] rounded w-3/4" />
        </div>
      ))}
    </div>
  );

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-lg text-[var(--text)]">Competence</h1>
          <p className="text-xs text-[var(--text-muted)] font-mono mt-0.5">
            W_s (soft) · W_h (hard) · W_eff (effective vote weight)
          </p>
        </div>
        <button onClick={() => setShowClaimModal(true)}
          className="btn btn-ghost text-xs gap-1.5">
          + W_h claim
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[var(--border)]">
        {[
          { key: "scores",      label: "My scores" },
          { key: "leaderboard", label: "Leaderboard" },
          { key: "claims",      label: `W_h claims${claims.length ? ` (${claims.length})` : ""}` },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key as typeof tab)}
            className={`px-4 py-2.5 text-xs font-mono transition-colors border-b-2 -mb-px ${
              tab === t.key
                ? "text-[var(--gold)] border-[var(--gold)]"
                : "text-[var(--text-muted)] border-transparent hover:text-[var(--text)]"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* My scores */}
      {tab === "scores" && (
        <div className="space-y-3">
          {scores.length === 0 ? (
            <div className="card p-10 text-center">
              <p className="text-sm font-mono text-[var(--text-muted)]">
                No competence scores yet.
              </p>
              <p className="text-xs text-[var(--text-dim)] mt-1">
                Participate in formal reviews and STF panels to earn W_s.
              </p>
            </div>
          ) : scores.map(s => (
            <div key={s.dormain_id} className="card p-4">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <p className="text-sm font-mono text-[var(--text)]">{s.dormain_name}</p>
                  {s.mcmp_status !== "active" && (
                    <p className={`text-[10px] font-mono mt-0.5 ${MCMP_STYLE[s.mcmp_status] ?? "text-zinc-400"}`}>
                      {s.mcmp_status}
                    </p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xl font-mono text-[var(--gold)]">{s.w_eff.toFixed(0)}</p>
                  <p className="text-[9px] font-mono text-[var(--text-dim)]">W_eff</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs font-mono mb-3">
                <div>
                  <p className="text-[var(--text-dim)]">W_s (soft / dynamic)</p>
                  <p className="text-[var(--text)] font-medium mt-0.5">{s.w_s.toFixed(1)}</p>
                </div>
                <div>
                  <p className="text-[var(--text-dim)]">W_h (hard / verified)</p>
                  <p className="text-[var(--gold)] font-medium mt-0.5">{s.w_h.toFixed(1)}</p>
                </div>
              </div>

              {/* W_s bar */}
              <div>
                <div className="flex justify-between text-[9px] font-mono
                  text-[var(--text-dim)] mb-1">
                  <span>0</span><span>3000</span>
                </div>
                <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                  <div className="h-full bg-[var(--gold)] rounded-full transition-all"
                    style={{ width: `${(s.w_s / 3000) * 100}%` }} />
                </div>
              </div>

              {s.last_activity_at && (
                <p className="text-[10px] font-mono text-[var(--text-dim)] mt-2">
                  Last activity{" "}
                  {new Date(s.last_activity_at).toLocaleDateString("en-GB", {
                    day: "numeric", month: "short", year: "numeric",
                  })}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Leaderboard */}
      {tab === "leaderboard" && (
        <div>
          <div className="mb-4">
            <select value={selectedDormain} onChange={e => setSelectedDormain(e.target.value)}
              className="bg-[var(--surface)] border border-[var(--border)] rounded
                px-3 py-1.5 text-xs font-mono text-[var(--text)]
                focus:outline-none focus:border-[var(--gold)]">
              {dormains.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
          <div className="card overflow-hidden">
            {leaderboard.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-sm font-mono text-[var(--text-muted)]">
                  No scores in this dormain yet.
                </p>
              </div>
            ) : leaderboard.map((entry, i) => (
              <div key={entry.member_id}
                className="flex items-center gap-4 px-4 py-3
                  border-b border-[var(--border)] last:border-0">
                <span className={`text-xs font-mono w-5 text-right shrink-0 ${
                  i === 0 ? "text-[var(--gold)]" :
                  i === 1 ? "text-zinc-400" :
                  i === 2 ? "text-amber-700" : "text-[var(--text-dim)]"
                }`}>
                  {entry.rank}
                </span>
                <div className="w-7 h-7 rounded-full bg-[var(--surface-raised)]
                  border border-[var(--border)] flex items-center justify-center shrink-0">
                  <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase">
                    {entry.handle[0]}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-mono text-[var(--text)]">{entry.handle}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <div className="text-right">
                    <p className="text-sm font-mono text-[var(--gold)]">{entry.w_s.toFixed(0)}</p>
                    <p className="text-[9px] font-mono text-[var(--text-dim)]">W_s</p>
                  </div>
                  {entry.w_h > 0 && (
                    <div className="text-right">
                      <p className="text-sm font-mono text-blue-400">{entry.w_h.toFixed(0)}</p>
                      <p className="text-[9px] font-mono text-[var(--text-dim)]">W_h</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* W_h claims */}
      {tab === "claims" && (
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <p className="text-xs font-mono text-[var(--text-muted)]">
              Claims undergo vSTF peer verification before W_h is updated.
            </p>
            <button onClick={() => setShowClaimModal(true)}
              className="btn btn-ghost text-xs">+ New claim</button>
          </div>

          {claims.length === 0 ? (
            <div className="card p-10 text-center">
              <p className="text-sm font-mono text-[var(--text-muted)]">No W_h claims filed.</p>
              <button onClick={() => setShowClaimModal(true)}
                className="text-xs text-[var(--gold)] hover:underline mt-2 block mx-auto">
                Submit your first claim →
              </button>
            </div>
          ) : claims.map(c => (
            <div key={c.id} className="card p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-mono text-[var(--text)]">{c.dormain_name}</p>
                  <p className="text-[10px] font-mono text-[var(--text-muted)] mt-0.5 capitalize">
                    {c.credential_type.replace("_", " ")}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-sm font-mono text-[var(--gold)]">
                    {c.claimed_value_wh.toFixed(0)}
                  </span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border
                    ${CLAIM_STATUS_STYLE[c.status] ?? "text-zinc-400 border-zinc-700"}`}>
                    {c.status === "wh_preliminary" ? "pending"
                      : c.status === "wh_verified" ? "verified"
                      : c.status === "vstf_pending" ? "in review"
                      : c.status}
                  </span>
                </div>
              </div>
              {c.status === "wh_verified" && c.verified_at && (
                <p className="text-[10px] font-mono text-emerald-400 mt-2 flex items-center gap-1">
                  <CheckCircle size={9} />
                  Verified {new Date(c.verified_at).toLocaleDateString("en-GB", {
                    day: "numeric", month: "short", year: "numeric",
                  })}
                </p>
              )}
              {c.status === "vstf_pending" && (
                <p className="text-[10px] font-mono text-blue-400 mt-2 flex items-center gap-1">
                  <Clock size={9} /> Under vSTF review
                </p>
              )}
              {c.expires_at && new Date(c.expires_at) < new Date() && (
                <p className="text-[10px] font-mono text-red-400 mt-2 flex items-center gap-1">
                  <AlertCircle size={9} /> Expired — resubmit
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {showClaimModal && (
        <WhClaimModal
          dormains={dormains}
          onClose={() => setShowClaimModal(false)}
          onSuccess={() => { setShowClaimModal(false); load(); setTab("claims"); }}
        />
      )}
    </div>
  );
}
