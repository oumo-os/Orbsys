"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { ChevronLeft, CheckCircle, XCircle, Clock, AlertCircle, Lock } from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Member { id: string; handle: string; display_name: string }
interface Circle { id: string; name: string }

interface MotionDirective {
  body: string;
  commitments: string[] | null;
  ambiguities_flagged: string[] | null;
}

interface MotionSpec {
  id: string;
  parameter: string;
  new_value: Record<string, unknown>;
  justification: string;
  pre_validation_status: string;
}

interface Gate2Diff {
  parameter: string;
  specified_value: Record<string, unknown>;
  applied_value: Record<string, unknown> | null;
  match: boolean;
  checked_at: string;
}

interface Resolution {
  id: string;
  resolution_ref: string;
  state: string;
  implementation_type: string;
  gate2_agent: string;
  implementing_circles: Circle[] | null;
  gate2_diffs: Gate2Diff[];
  enacted_at: string | null;
  created_at: string;
}

interface Motion {
  id: string;
  org_id: string;
  cell_id: string;
  motion_type: string;
  state: string;
  filed_by: Member | null;
  directive: MotionDirective | null;
  specifications: MotionSpec[];
  implementing_circle_ids: string[] | null;
  implementing_circles: Circle[] | null;
  resolution: Resolution | null;
  created_at: string;
  crystallised_at: string | null;
  state_changed_at: string;
}

// ── State visuals ─────────────────────────────────────────────────────────────

const STATE_CONFIG: Record<string, { icon: React.ElementType; colour: string; label: string }> = {
  draft:                  { icon: Clock,         colour: "text-zinc-400",   label: "Draft" },
  active:                 { icon: Clock,         colour: "text-blue-400",   label: "Voting open" },
  gate1_pending:          { icon: AlertCircle,   colour: "text-amber-400",  label: "Gate 1 review" },
  gate1_approved:         { icon: CheckCircle,   colour: "text-emerald-400",label: "Gate 1 approved" },
  gate1_rejected:         { icon: XCircle,       colour: "text-red-400",    label: "Gate 1 rejected" },
  revision_requested:     { icon: AlertCircle,   colour: "text-amber-400",  label: "Revision requested" },
  pending_implementation: { icon: Clock,         colour: "text-blue-400",   label: "Pending implementation" },
  gate2_pending:          { icon: AlertCircle,   colour: "text-amber-400",  label: "Gate 2 review" },
  enacted:                { icon: CheckCircle,   colour: "text-emerald-400",label: "Enacted" },
  enacted_locked:         { icon: Lock,          colour: "text-emerald-400",label: "Enacted & locked" },
  contested:              { icon: XCircle,       colour: "text-red-400",    label: "Contested" },
  abandoned:              { icon: XCircle,       colour: "text-zinc-500",   label: "Abandoned" },
};

const TRACK_STEPS = [
  { key: "filed",    keys: ["draft", "active"],          label: "Filed" },
  { key: "voted",    keys: ["gate1_pending"],             label: "Voted" },
  { key: "gate1",    keys: ["gate1_approved", "gate1_rejected", "revision_requested"], label: "Gate 1" },
  { key: "pending",  keys: ["pending_implementation", "gate2_pending"], label: "Impl." },
  { key: "enacted",  keys: ["enacted", "enacted_locked"], label: "Enacted" },
];

function MotionStateTrack({ state }: { state: string }) {
  const currentGroupIdx = TRACK_STEPS.findIndex(g =>
    g.keys.includes(state) || (g.key === "filed" && state === "draft")
  );
  const isRejected = state === "gate1_rejected" || state === "abandoned" || state === "contested";

  return (
    <div className="flex items-center gap-2 mt-3">
      {TRACK_STEPS.map((step, i) => {
        const done = i < currentGroupIdx;
        const active = i === currentGroupIdx;
        const blocked = isRejected && i >= currentGroupIdx;
        return (
          <div key={step.key} className="flex items-center gap-2 flex-1">
            <div className={`flex-1 h-1.5 rounded-full transition-colors ${
              blocked ? "bg-red-800/60" :
              done    ? "bg-emerald-600" :
              active  ? "bg-[var(--gold)]" :
                        "bg-[var(--border)]"
            }`} />
            {i === TRACK_STEPS.length - 1 && (
              <span className={`text-[9px] font-mono whitespace-nowrap ${
                done || active ? "text-[var(--text-muted)]" : "text-[var(--text-dim)]"
              }`}>
                {step.label}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function Badge({ text, colour }: { text: string; colour: string }) {
  return (
    <span className={`text-[10px] font-mono px-2 py-0.5 rounded border border-current/30 ${colour}`}>
      {text}
    </span>
  );
}

function ValidationBadge({ status }: { status: string }) {
  const map: Record<string, [string, string]> = {
    valid:   ["Valid", "text-emerald-400"],
    pending: ["Pending", "text-amber-400"],
    invalid_range:     ["Out of range", "text-red-400"],
    invalid_parameter: ["Unknown param", "text-red-400"],
    missing_justification: ["Needs justification", "text-amber-400"],
  };
  const [label, colour] = map[status] ?? ["Unknown", "text-zinc-400"];
  return <Badge text={label} colour={colour} />;
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function MotionPage() {
  const { id } = useParams<{ id: string }>();
  const [motion, setMotion] = useState<Motion | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await api.get(`/motions/${id}`);
      setMotion(res.data as Motion);
    } catch {
      setErr("Motion not found.");
    } finally { setLoading(false); }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div className="space-y-4">
      {[1, 2].map(i => (
        <div key={i} className="card p-5 animate-pulse">
          <div className="h-3 bg-[var(--surface-raised)] rounded w-1/3 mb-3" />
          <div className="h-2 bg-[var(--surface-raised)] rounded w-full mb-1.5" />
          <div className="h-2 bg-[var(--surface-raised)] rounded w-4/5" />
        </div>
      ))}
    </div>
  );

  if (err || !motion) return (
    <div className="text-center py-16">
      <p className="text-sm font-mono text-[var(--text-muted)]">{err ?? "Not found"}</p>
      <Link href="/org/motions" className="text-xs text-[var(--gold)] hover:underline mt-2 block">
        ← Motions
      </Link>
    </div>
  );

  const stateConf = STATE_CONFIG[motion.state] ?? STATE_CONFIG.draft;
  const StateIcon = stateConf.icon;
  const res = motion.resolution;
  const isEnacted = motion.state === "enacted" || motion.state === "enacted_locked";
  const isLocked = motion.state === "enacted_locked";

  return (
    <div className="space-y-5">
      <Link href="/org/motions"
        className="inline-flex items-center gap-1.5 text-xs font-mono
          text-[var(--text-muted)] hover:text-[var(--text)] transition-colors">
        <ChevronLeft size={12} /> Motions
      </Link>

      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {res && (
              <p className="text-[10px] font-mono text-[var(--gold)] mb-1">
                {res.resolution_ref}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border
                border-current/30 ${stateConf.colour}`}>
                {motion.motion_type.replace("_", "-")}
              </span>
              <div className={`flex items-center gap-1 text-xs font-mono ${stateConf.colour}`}>
                <StateIcon size={12} />
                {stateConf.label}
              </div>
              {isLocked && (
                <span className="flex items-center gap-1 text-[10px] font-mono
                  text-[var(--text-dim)]">
                  <Lock size={9} /> Immutable
                </span>
              )}
            </div>
            <MotionStateTrack state={motion.state} />
          </div>
        </div>

        <div className="flex flex-wrap gap-3 mt-4 pt-3 border-t border-[var(--border)]
          text-[10px] font-mono text-[var(--text-muted)]">
          {motion.filed_by && (
            <span>Filed by @{motion.filed_by.handle}</span>
          )}
          <span>·</span>
          <span>
            {new Date(motion.created_at).toLocaleDateString("en-GB", {
              day: "numeric", month: "short", year: "numeric",
            })}
          </span>
          <span>·</span>
          <Link href={`/org/cells/${motion.cell_id}`}
            className="text-[var(--gold)] hover:underline">
            View cell →
          </Link>
        </div>
      </div>

      {/* Directive */}
      {motion.directive && (
        <div className="card p-5">
          <p className="section-label mb-3">Directive</p>
          <p className="text-sm text-[var(--text)] leading-relaxed whitespace-pre-wrap font-body">
            {motion.directive.body}
          </p>
          {motion.directive.commitments && motion.directive.commitments.length > 0 && (
            <div className="mt-4">
              <p className="text-[10px] font-mono text-[var(--text-dim)] uppercase tracking-wider mb-2">
                Commitments
              </p>
              <ul className="space-y-1.5">
                {motion.directive.commitments.map((c, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <span className="text-[var(--gold)] mt-0.5 shrink-0">◎</span>
                    <span className="text-[var(--text)]">{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {motion.directive.ambiguities_flagged && motion.directive.ambiguities_flagged.length > 0 && (
            <div className="mt-4 p-3 rounded bg-amber-900/20 border border-amber-800/40">
              <p className="text-[10px] font-mono text-amber-400 uppercase tracking-wider mb-2">
                Flagged ambiguities
              </p>
              <ul className="space-y-1">
                {motion.directive.ambiguities_flagged.map((a, i) => (
                  <li key={i} className="text-xs text-amber-200 flex gap-2">
                    <span className="shrink-0">·</span>{a}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {motion.implementing_circles && motion.implementing_circles.length > 0 && (
            <div className="mt-4 pt-3 border-t border-[var(--border)]">
              <p className="text-[10px] font-mono text-[var(--text-dim)] uppercase tracking-wider mb-2">
                Implementing circles
              </p>
              <div className="flex flex-wrap gap-1.5">
                {motion.implementing_circles.map(c => (
                  <span key={c.id} className="text-xs font-mono px-2 py-0.5 rounded
                    bg-[var(--surface-raised)] border border-[var(--border)] text-[var(--text)]">
                    {c.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Specifications */}
      {motion.specifications.length > 0 && (
        <div className="card p-5">
          <p className="section-label mb-3">
            Specifications
            <span className="ml-2 text-[var(--text-dim)] normal-case">
              ({motion.specifications.length} parameter{motion.specifications.length !== 1 ? "s" : ""})
            </span>
          </p>
          <div className="space-y-3">
            {motion.specifications.map(s => (
              <div key={s.id} className="p-3 rounded bg-[var(--surface-raised)]
                border border-[var(--border)]">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <code className="text-xs font-mono text-[var(--gold)]">{s.parameter}</code>
                  <ValidationBadge status={s.pre_validation_status} />
                </div>
                <div className="font-mono text-xs text-[var(--text)] mb-2">
                  → {JSON.stringify(s.new_value.value ?? s.new_value)}
                </div>
                <p className="text-xs text-[var(--text-muted)]">{s.justification}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Resolution */}
      {res && (
        <div className={`card p-5 ${isEnacted ? "border-emerald-800/40" : ""}`}>
          <div className="flex items-center justify-between mb-3">
            <p className="section-label">Resolution</p>
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-mono text-[var(--gold)]">{res.resolution_ref}</span>
              {isEnacted && <CheckCircle size={12} className="text-emerald-400" />}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs font-mono mb-4">
            {[
              ["State", res.state.replace("_", " ")],
              ["Implementation", res.implementation_type.replace("_", " ")],
              ["Gate 2 agent", res.gate2_agent.replace("_", " ")],
              ["Created", new Date(res.created_at).toLocaleDateString("en-GB", {
                day: "numeric", month: "short", year: "numeric",
              })],
              ...(res.enacted_at ? [["Enacted", new Date(res.enacted_at).toLocaleDateString("en-GB", {
                day: "numeric", month: "short", year: "numeric",
              })]] : []),
            ].map(([k, v]) => (
              <div key={k}>
                <span className="text-[var(--text-dim)]">{k}</span>
                <p className="text-[var(--text)] capitalize mt-0.5">{v}</p>
              </div>
            ))}
          </div>

          {/* Gate 2 diffs */}
          {res.gate2_diffs.length > 0 && (
            <div>
              <p className="text-[10px] font-mono text-[var(--text-dim)] uppercase
                tracking-wider mb-2">
                Gate 2 diff
              </p>
              <div className="space-y-2">
                {res.gate2_diffs.map((d, i) => (
                  <div key={i}
                    className={`p-2.5 rounded text-xs font-mono border ${
                      d.match
                        ? "bg-emerald-900/20 border-emerald-800/40"
                        : "bg-red-900/20 border-red-800/40"
                    }`}>
                    <div className="flex items-center justify-between">
                      <code className={d.match ? "text-emerald-400" : "text-red-400"}>
                        {d.parameter}
                      </code>
                      {d.match
                        ? <CheckCircle size={11} className="text-emerald-400" />
                        : <XCircle size={11} className="text-red-400" />
                      }
                    </div>
                    <div className="mt-1 text-[10px] text-[var(--text-muted)]">
                      spec: {JSON.stringify(d.specified_value.value ?? d.specified_value)}
                      {d.applied_value && (
                        <> → applied: {JSON.stringify(d.applied_value.value ?? d.applied_value)}</>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
