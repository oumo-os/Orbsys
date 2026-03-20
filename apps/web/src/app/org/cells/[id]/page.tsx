"use client";

import { useEffect, useState, useCallback, FormEvent, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { cellsApi, competenceApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import {
  ChevronLeft, Send, Vote, Zap, FileText,
  Users, Clock, CheckCircle, XCircle, AlertCircle,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Member { id: string; handle: string; display_name: string }

interface Cell {
  id: string;
  org_id: string;
  cell_type: string;
  state: string;
  visibility: string;
  initiating_member: Member | null;
  founding_mandate: string | null;
  revision_directive: string | null;
  invited_circles: { id: string; name: string }[];
  created_at: string;
  state_changed_at: string;
}

interface Contribution {
  id: string;
  cell_id: string;
  author: Member | null;
  body: string;
  contribution_type: string;
  created_at: string;
}

interface VoteTally {
  motion_id: string;
  dormain_id: string;
  dormain_name: string;
  yea_weight: number;
  nay_weight: number;
  abstain_weight: number;
  total_weight: number;
  yea_count: number;
  nay_count: number;
  abstain_count: number;
  quorum_met: boolean;
  threshold_met: boolean;
}

interface VoteSummary { motion_id: string; tallies_by_dormain: VoteTally[] }

interface FiledMotion {
  id: string;
  motion_type: string;
  state: string;
  cell_id: string;
  filed_by: Member;
  implementing_circle_ids: string[] | null;
  created_at: string;
}

interface CrystalliseDraft {
  draft_id: string;
  motion_type_suggested: string;
  directive_draft: {
    body: string;
    commitments: string[];
    ambiguities_flagged: string[];
    contributing_members: Member[];
  } | null;
  specification_drafts: {
    parameter: string;
    new_value: unknown;
    justification: string;
  }[] | null;
}

interface Dormain { id: string; name: string }

// ── Helpers ───────────────────────────────────────────────────────────────────

const CELL_STATE_COLOURS: Record<string, string> = {
  active:      "text-emerald-400 border-emerald-800/40 bg-emerald-900/20",
  temporarily_closed: "text-amber-400 border-amber-800/40 bg-amber-900/20",
  archived:    "text-zinc-400 border-zinc-700 bg-zinc-800/40",
  dissolved:   "text-zinc-500 border-zinc-700 bg-zinc-800/20",
  suspended:   "text-red-400 border-red-800/40 bg-red-900/20",
};

const MOTION_STATE_STEPS = [
  { key: "draft",        label: "Draft" },
  { key: "active",       label: "Voted" },
  { key: "gate1_pending", label: "Gate 1" },
  { key: "gate1_approved", label: "Approved" },
  { key: "pending_implementation", label: "Pending" },
  { key: "enacted",      label: "Enacted" },
];

function MotionTrack({ state }: { state: string }) {
  const idx = MOTION_STATE_STEPS.findIndex(s => s.key === state);
  return (
    <div className="flex items-center gap-0 mt-2">
      {MOTION_STATE_STEPS.map((step, i) => {
        const cls = i < idx ? "completed" : i === idx ? "active" :
          (state === "gate1_rejected" || state === "abandoned") && i > 0 ? "blocked" : "";
        return (
          <div key={step.key} title={step.label}
            className={`motion-step ${cls}`} style={{ flex: 1 }} />
        );
      })}
    </div>
  );
}

function rel(iso: string) {
  const d = Date.now() - new Date(iso).getTime();
  const m = Math.floor(d / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Sub-panels ────────────────────────────────────────────────────────────────

function ContributionItem({ c }: { c: Contribution }) {
  const typeLabel: Record<string, string> = {
    discussion: "",
    evidence: "Evidence",
    proposal: "Proposal",
    commons_context_import: "↩ Commons",
  };
  return (
    <div className="py-4 border-b border-[var(--border)] last:border-0">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-[var(--surface-raised)] border border-[var(--border)]
            flex items-center justify-center text-[10px] font-mono text-[var(--text-muted)] uppercase">
            {c.author?.handle?.[0] ?? "?"}
          </div>
          <span className="text-xs font-mono text-[var(--text)]">{c.author?.handle ?? "—"}</span>
          {typeLabel[c.contribution_type] && (
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded
              bg-[var(--blue-dim)] text-[var(--blue)] border border-[var(--blue)]/20">
              {typeLabel[c.contribution_type]}
            </span>
          )}
        </div>
        <span className="text-[10px] font-mono text-[var(--text-dim)]">{rel(c.created_at)}</span>
      </div>
      <p className="text-sm text-[var(--text)] leading-relaxed whitespace-pre-wrap pl-8">
        {c.body}
      </p>
    </div>
  );
}

function VotePanel({
  votes,
  dormains,
  cellId,
  isInitiator,
  onVoteCast,
}: {
  votes: VoteSummary | null;
  dormains: Dormain[];
  cellId: string;
  isInitiator: boolean;
  onVoteCast: () => void;
}) {
  const [dormainId, setDormainId] = useState("");
  const [choice, setChoice] = useState<"yea" | "nay" | "abstain">("yea");
  const [casting, setCasting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const motionId = votes?.motion_id;

  async function castVote(e: FormEvent) {
    e.preventDefault();
    if (!motionId || !dormainId) return;
    setCasting(true); setErr(null);
    try {
      await cellsApi.castVote(cellId, { motion_id: motionId, dormain_id: dormainId, vote: choice });
      onVoteCast();
      setDormainId("");
    } catch (ex: unknown) {
      const msg = (ex as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Vote failed";
      setErr(msg);
    } finally { setCasting(false); }
  }

  if (!votes || !motionId) {
    return (
      <div className="text-center py-8">
        <Vote size={28} className="mx-auto mb-2 text-[var(--text-dim)]" />
        <p className="text-xs font-mono text-[var(--text-muted)]">
          No active motion — crystallise first
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {votes.tallies_by_dormain.length > 0 && (
        <div className="space-y-3">
          {votes.tallies_by_dormain.map(t => {
            const total = t.total_weight || 1;
            return (
              <div key={t.dormain_id}
                className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--border)]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-[var(--text)]">{t.dormain_name}</span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                    t.threshold_met
                      ? "text-emerald-400 border-emerald-800/40 bg-emerald-900/20"
                      : "text-amber-400 border-amber-800/40 bg-amber-900/20"
                  }`}>
                    {t.threshold_met ? "Passing" : "Failing"}
                  </span>
                </div>
                <div className="h-2 bg-[var(--border)] rounded-full overflow-hidden flex">
                  <div className="h-full bg-emerald-500 transition-all"
                    style={{ width: `${(t.yea_weight / total) * 100}%` }} />
                  <div className="h-full bg-red-500 transition-all"
                    style={{ width: `${(t.nay_weight / total) * 100}%` }} />
                </div>
                <div className="flex gap-3 mt-1 text-[10px] font-mono text-[var(--text-muted)]">
                  <span className="text-emerald-400">
                    Yea {t.yea_weight.toFixed(0)} ({t.yea_count})
                  </span>
                  <span className="text-red-400">
                    Nay {t.nay_weight.toFixed(0)} ({t.nay_count})
                  </span>
                  {t.abstain_count > 0 && (
                    <span>Abs {t.abstain_weight.toFixed(0)} ({t.abstain_count})</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <form onSubmit={castVote} className="space-y-2 pt-2 border-t border-[var(--border)]">
        <p className="section-label">Cast vote</p>
        <select value={dormainId} onChange={e => setDormainId(e.target.value)} required
          className="w-full bg-[var(--surface)] border border-[var(--border)] rounded px-3 py-2
            text-sm font-mono text-[var(--text)] focus:outline-none focus:border-[var(--gold)]">
          <option value="">Select dormain…</option>
          {dormains.map(d => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
        <div className="grid grid-cols-3 gap-2">
          {(["yea", "nay", "abstain"] as const).map(v => (
            <button key={v} type="button" onClick={() => setChoice(v)}
              className={`py-2 rounded text-xs font-mono border transition-all ${
                choice === v
                  ? v === "yea"
                    ? "bg-emerald-500/20 border-emerald-500/60 text-emerald-400"
                    : v === "nay"
                    ? "bg-red-500/20 border-red-500/60 text-red-400"
                    : "bg-[var(--surface-raised)] border-[var(--border)] text-[var(--text)]"
                  : "bg-transparent border-[var(--border)] text-[var(--text-muted)] hover:border-[var(--border)]"
              }`}>
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
        {err && <p className="text-[11px] font-mono text-red-400">{err}</p>}
        <button type="submit" disabled={casting || !dormainId}
          className="w-full btn btn-primary text-xs disabled:opacity-40">
          {casting ? "Casting…" : "Cast vote"}
        </button>
      </form>
    </div>
  );
}

// ── Crystallise / File Motion modal ──────────────────────────────────────────

function CrystalliseModal({
  draft,
  dormains,
  circles,
  cellId,
  onFiled,
  onClose,
}: {
  draft: CrystalliseDraft;
  dormains: Dormain[];
  circles: { id: string; name: string }[];
  cellId: string;
  onFiled: (motion: FiledMotion) => void;
  onClose: () => void;
}) {
  const [motionType, setMotionType] = useState(draft.motion_type_suggested ?? "non_system");
  const [directiveBody, setDirectiveBody] = useState(draft.directive_draft?.body ?? "");
  const [commitments, setCommitments] = useState(
    (draft.directive_draft?.commitments ?? []).join("\n")
  );
  const [implementing, setImplementing] = useState<string[]>([]);
  const [filing, setFiling] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setFiling(true); setErr(null);
    try {
      const body: Record<string, unknown> = {
        motion_type: motionType,
        directive_body: directiveBody || null,
        directive_commitments: commitments.split("\n").filter(Boolean),
        implementing_circle_ids: implementing.length ? implementing : undefined,
      };
      const res = await cellsApi.fileMotion(cellId, body);
      onFiled(res.data as FiledMotion);
    } catch (ex: unknown) {
      const msg = (ex as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Filing failed";
      setErr(msg);
    } finally { setFiling(false); }
  }

  const needsCircles = motionType === "non_system" || motionType === "hybrid";

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="card w-full max-w-xl my-auto">
        <div className="p-6 border-b border-[var(--border)] flex items-center justify-between">
          <div>
            <h2 className="font-display text-base text-[var(--text)]">File motion</h2>
            <p className="text-xs font-mono text-[var(--text-muted)] mt-0.5">
              Insight Engine draft — edit before filing
            </p>
          </div>
          <button onClick={onClose}
            className="text-[var(--text-muted)] hover:text-[var(--text)] text-xl leading-none">×</button>
        </div>

        <form onSubmit={submit} className="p-6 space-y-5">
          {/* Motion type */}
          <div>
            <label className="section-label block mb-2">Motion type</label>
            <div className="flex gap-2">
              {["non_system", "sys_bound", "hybrid"].map(t => (
                <button key={t} type="button" onClick={() => setMotionType(t)}
                  className={`flex-1 py-2 text-xs font-mono rounded border transition-all ${
                    motionType === t
                      ? "bg-[var(--gold-glow)] border-[var(--gold)] text-[var(--gold)]"
                      : "border-[var(--border)] text-[var(--text-muted)] hover:border-[var(--border)]"
                  }`}>
                  {t === "non_system" ? "Non-system" : t === "sys_bound" ? "Sys-bound" : "Hybrid"}
                </button>
              ))}
            </div>
          </div>

          {/* Directive (non_system / hybrid) */}
          {(motionType === "non_system" || motionType === "hybrid") && (
            <div>
              <label className="section-label block mb-2">Directive</label>
              <textarea value={directiveBody} onChange={e => setDirectiveBody(e.target.value)}
                rows={6} required
                className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                  px-3 py-2 text-sm text-[var(--text)] font-body resize-none
                  focus:outline-none focus:border-[var(--gold)]"
                placeholder="The directive statement…" />
            </div>
          )}

          {/* Commitments */}
          {(motionType === "non_system" || motionType === "hybrid") && (
            <div>
              <label className="section-label block mb-2">
                Commitments <span className="normal-case text-[var(--text-dim)]">(one per line)</span>
              </label>
              <textarea value={commitments} onChange={e => setCommitments(e.target.value)}
                rows={3}
                className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                  px-3 py-2 text-sm font-mono text-[var(--text)] resize-none
                  focus:outline-none focus:border-[var(--gold)]"
                placeholder="Each commitment on its own line…" />
            </div>
          )}

          {/* Implementing circles (required for non_system / hybrid) */}
          {needsCircles && circles.length > 0 && (
            <div>
              <label className="section-label block mb-2">
                Implementing circles <span className="text-red-400">*</span>
              </label>
              <div className="space-y-1.5 max-h-36 overflow-y-auto">
                {circles.map(c => (
                  <label key={c.id} className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" className="accent-[var(--gold)]"
                      checked={implementing.includes(c.id)}
                      onChange={e => setImplementing(prev =>
                        e.target.checked ? [...prev, c.id] : prev.filter(x => x !== c.id)
                      )} />
                    <span className="text-xs font-mono text-[var(--text)]">{c.name}</span>
                  </label>
                ))}
              </div>
              {needsCircles && implementing.length === 0 && (
                <p className="text-[10px] font-mono text-amber-400 mt-1">
                  At least one implementing circle required
                </p>
              )}
            </div>
          )}

          {err && (
            <div className="text-xs font-mono text-red-400 bg-[var(--red-dim)] border
              border-red-800/40 rounded px-3 py-2">
              {err}
            </div>
          )}

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} className="btn btn-ghost flex-1 text-xs">
              Cancel
            </button>
            <button type="submit"
              disabled={filing || (needsCircles && implementing.length === 0)}
              className="btn btn-primary flex-1 text-xs disabled:opacity-40">
              {filing ? "Filing…" : "File motion"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CellPage() {
  const { id } = useParams<{ id: string }>();
  const member = useAuthStore(s => s.member);

  const [cell, setCell] = useState<Cell | null>(null);
  const [contribs, setContribs] = useState<Contribution[]>([]);
  const [votes, setVotes] = useState<VoteSummary | null>(null);
  const [dormains, setDormains] = useState<Dormain[]>([]);
  const [activeMotion, setActiveMotion] = useState<FiledMotion | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [tab, setTab] = useState<"contributions" | "vote">("contributions");
  const [newBody, setNewBody] = useState("");
  const [posting, setPosting] = useState(false);
  const [crystallising, setCrystallising] = useState(false);
  const [draft, setDraft] = useState<CrystalliseDraft | null>(null);
  const [showModal, setShowModal] = useState(false);

  const endRef = useRef<HTMLDivElement>(null);

  const isInitiator = cell?.initiating_member?.id === member?.id;

  const load = useCallback(async () => {
    try {
      const [cellRes, contribRes, votesRes, dormainRes] = await Promise.all([
        cellsApi.get(id),
        cellsApi.contributions(id),
        cellsApi.votes(id).catch(() => ({ data: null })),
        competenceApi.dormains(),
      ]);
      setCell(cellRes.data);
      const items = contribRes.data?.items ?? contribRes.data ?? [];
      setContribs(Array.isArray(items) ? items : []);
      setVotes(votesRes.data as VoteSummary | null);
      setDormains(dormainRes.data ?? []);
    } catch {
      setErr("Cell not found or access denied.");
    } finally { setLoading(false); }
  }, [id]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (tab === "contributions") {
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    }
  }, [contribs, tab]);

  async function postContribution(e: FormEvent) {
    e.preventDefault();
    if (!newBody.trim()) return;
    setPosting(true);
    try {
      await cellsApi.addContribution(id, { body: newBody.trim(), contribution_type: "discussion" });
      setNewBody("");
      load();
    } catch (ex: unknown) {
      alert((ex as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed");
    } finally { setPosting(false); }
  }

  async function crystallise() {
    setCrystallising(true);
    try {
      const res = await cellsApi.crystallise(id);
      setDraft(res.data as CrystalliseDraft);
      setShowModal(true);
    } catch (ex: unknown) {
      alert((ex as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed");
    } finally { setCrystallising(false); }
  }

  function handleFiled(motion: FiledMotion) {
    setActiveMotion(motion);
    setShowModal(false);
    setDraft(null);
    setTab("vote");
    load();
  }

  if (loading) return (
    <div className="space-y-4">
      {[1, 2, 3].map(i => (
        <div key={i} className="card p-5 animate-pulse">
          <div className="h-3 bg-[var(--surface-raised)] rounded w-1/2 mb-2" />
          <div className="h-2 bg-[var(--surface-raised)] rounded w-full" />
        </div>
      ))}
    </div>
  );

  if (err || !cell) return (
    <div className="text-center py-16">
      <p className="text-sm font-mono text-[var(--text-muted)]">{err ?? "Not found"}</p>
      <Link href="/org/commons" className="text-xs text-[var(--gold)] hover:underline mt-2 block">
        ← Commons
      </Link>
    </div>
  );

  const isActive = cell.state === "active";
  const stateClass = CELL_STATE_COLOURS[cell.state] ?? CELL_STATE_COLOURS.active;
  const hasMotion = !!votes?.motion_id || !!activeMotion;

  return (
    <div className="space-y-5">
      {/* Back */}
      <Link href="/org/cells"
        className="inline-flex items-center gap-1.5 text-xs font-mono
          text-[var(--text-muted)] hover:text-[var(--text)] transition-colors">
        <ChevronLeft size={12} /> Cells
      </Link>

      {/* Cell header */}
      <div className="card p-5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[9px] font-mono uppercase tracking-widest text-[var(--text-dim)]">
                {cell.cell_type}
              </span>
              <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${stateClass}`}>
                {cell.state}
              </span>
            </div>
            {cell.founding_mandate ? (
              <p className="text-sm text-[var(--text)] leading-relaxed">
                {cell.founding_mandate}
              </p>
            ) : (
              <p className="text-sm text-[var(--text-muted)] italic">No founding mandate set</p>
            )}
          </div>
        </div>

        {/* Revision directive */}
        {cell.revision_directive && (
          <div className="mt-3 p-3 rounded bg-amber-900/20 border border-amber-800/40">
            <p className="text-[9px] font-mono uppercase tracking-widest text-amber-400 mb-1">
              Revision directive
            </p>
            <p className="text-xs text-amber-200 leading-relaxed">{cell.revision_directive}</p>
          </div>
        )}

        {/* Circles + meta */}
        <div className="flex flex-wrap items-center gap-3 mt-3 pt-3 border-t border-[var(--border)]
          text-[10px] font-mono text-[var(--text-muted)]">
          {cell.invited_circles.length > 0 && (
            <div className="flex items-center gap-1.5">
              <Users size={10} />
              {cell.invited_circles.map(c => (
                <span key={c.id} className="px-1.5 py-0.5 rounded bg-[var(--surface-raised)]
                  border border-[var(--border)]">
                  {c.name}
                </span>
              ))}
            </div>
          )}
          <div className="flex items-center gap-1">
            <Clock size={10} />
            {new Date(cell.created_at).toLocaleDateString("en-GB", {
              day: "numeric", month: "short", year: "numeric",
            })}
          </div>
          {cell.initiating_member && (
            <span>Initiated by @{cell.initiating_member.handle}</span>
          )}
        </div>
      </div>

      {/* Active motion banner */}
      {hasMotion && votes?.motion_id && (
        <div className="card p-4 border-[var(--gold)]/30 bg-[var(--gold-glow)]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText size={14} className="text-[var(--gold)]" />
              <span className="text-xs font-mono text-[var(--gold)]">
                Active motion — voting open
              </span>
            </div>
            <Link href={`/org/motions/${votes.motion_id}`}
              className="text-[10px] font-mono text-[var(--gold)] hover:underline">
              View motion →
            </Link>
          </div>
          {activeMotion && <MotionTrack state={activeMotion.state} />}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[var(--border)]">
        {[
          { key: "contributions", label: `Contributions (${contribs.length})` },
          { key: "vote", label: "Vote" },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key as "contributions" | "vote")}
            className={`px-4 py-2.5 text-xs font-mono transition-colors border-b-2 -mb-px ${
              tab === t.key
                ? "text-[var(--gold)] border-[var(--gold)]"
                : "text-[var(--text-muted)] border-transparent hover:text-[var(--text)]"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "contributions" && (
        <div>
          <div className="space-y-0">
            {contribs.length === 0 ? (
              <div className="text-center py-10">
                <p className="text-sm font-mono text-[var(--text-muted)]">No contributions yet.</p>
                <p className="text-xs text-[var(--text-dim)] mt-1">
                  Be the first to add to this deliberation.
                </p>
              </div>
            ) : (
              contribs.map(c => <ContributionItem key={c.id} c={c} />)
            )}
            <div ref={endRef} />
          </div>

          {/* Compose */}
          {isActive && (
            <form onSubmit={postContribution}
              className="mt-4 pt-4 border-t border-[var(--border)] space-y-2">
              <textarea value={newBody} onChange={e => setNewBody(e.target.value)}
                rows={4} placeholder="Add to the deliberation…"
                className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                  px-3 py-2 text-sm text-[var(--text)] font-body resize-none
                  focus:outline-none focus:border-[var(--gold)] placeholder:text-[var(--text-dim)]" />
              <div className="flex items-center justify-between">
                <div className="flex gap-2">
                  {/* Crystallise — initiating member only, no existing motion */}
                  {isInitiator && !hasMotion && (
                    <button type="button" onClick={crystallise} disabled={crystallising}
                      className="btn btn-ghost text-xs gap-1.5 disabled:opacity-40">
                      <Zap size={12} className="text-[var(--gold)]" />
                      {crystallising ? "Generating draft…" : "Crystallise"}
                    </button>
                  )}
                </div>
                <button type="submit" disabled={posting || !newBody.trim()}
                  className="btn btn-primary text-xs gap-1.5 disabled:opacity-40">
                  <Send size={11} />
                  {posting ? "Posting…" : "Post"}
                </button>
              </div>
            </form>
          )}

          {!isActive && (
            <div className="mt-4 pt-4 border-t border-[var(--border)] text-center">
              <p className="text-xs font-mono text-[var(--text-muted)]">
                Cell is {cell.state} — no new contributions
              </p>
            </div>
          )}
        </div>
      )}

      {tab === "vote" && (
        <VotePanel
          votes={votes}
          dormains={dormains}
          cellId={id}
          isInitiator={isInitiator}
          onVoteCast={load}
        />
      )}

      {/* Crystallise modal */}
      {showModal && draft && (
        <CrystalliseModal
          draft={draft}
          dormains={dormains}
          circles={cell.invited_circles}
          cellId={id}
          onFiled={handleFiled}
          onClose={() => { setShowModal(false); setDraft(null); }}
        />
      )}
    </div>
  );
}
