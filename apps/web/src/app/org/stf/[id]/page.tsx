"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, stfApi } from "@/lib/api";
import { ChevronLeft, Shield, CheckCircle, Clock, AlertCircle } from "lucide-react";

interface Circle { id: string; name: string }

interface STFInstance {
  id: string;
  org_id: string;
  stf_type: string;
  state: string;
  mandate: string;
  commissioned_by_circle: Circle | null;
  motion_id: string | null;
  resolution_id: string | null;
  subject_member_id: string | null;
  deadline: string | null;
  assignment_count: number;
  verdicts_filed: number;
  created_at: string;
  completed_at: string | null;
}

interface Assignment {
  id: string;
  stf_instance_id: string;
  stf_type: string;
  member: { id: string; handle: string; display_name: string } | null;
  slot_type: string;
  assigned_at: string;
  rotation_end: string | null;
  verdict_filed_at: string | null;
}

interface VerdictAggregate {
  stf_instance_id: string;
  stf_type: string;
  state: string;
  total_assignments: number;
  verdicts_filed: number;
  counts: Record<string, number>;
  majority_verdict: string | null;
  completed_at: string | null;
}

const STF_TYPE_COLOUR: Record<string, string> = {
  xstf:      "var(--stf-xstf)",
  astf:      "var(--stf-astf)",
  astf_motion: "var(--stf-astf)",
  vstf:      "var(--stf-vstf)",
  jstf:      "var(--stf-jstf)",
  meta_astf: "var(--stf-meta)",
};

const BLIND_TYPES = new Set(["astf", "astf_motion", "astf_periodic", "vstf", "jstf", "meta_astf"]);

const VERDICT_COLOUR: Record<string, string> = {
  approve:   "text-emerald-400",
  clear:     "text-emerald-400",
  reject:    "text-red-400",
  violation: "text-red-400",
  revision_request: "text-amber-400",
  concerns:  "text-amber-400",
  adequate:  "text-blue-400",
  insufficient: "text-red-400",
};

function VerdictBar({ counts, total }: { counts: Record<string, number>; total: number }) {
  if (total === 0) return null;
  const colours = ["bg-emerald-500", "bg-red-500", "bg-amber-500", "bg-blue-500", "bg-zinc-500"];
  const entries = Object.entries(counts);
  return (
    <div className="flex h-2 rounded-full overflow-hidden gap-0.5">
      {entries.map(([v, count], i) => (
        <div key={v} title={`${v}: ${count}`}
          className={`h-full transition-all ${colours[i % colours.length]}`}
          style={{ width: `${(count / total) * 100}%` }} />
      ))}
    </div>
  );
}

export default function STFDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [stf, setStf] = useState<STFInstance | null>(null);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [aggregate, setAggregate] = useState<VerdictAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [enacting, setEnacting] = useState(false);
  const [enactResult, setEnactResult] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [stfRes, assignRes, verdictRes] = await Promise.all([
        stfApi.get(id),
        stfApi.assignments(id),
        stfApi.verdicts(id).catch(() => ({ data: null })),
      ]);
      setStf(stfRes.data as STFInstance);
      setAssignments((assignRes.data ?? []) as Assignment[]);
      setAggregate(verdictRes.data as VerdictAggregate | null);
    } catch {
      setErr("STF not found.");
    } finally { setLoading(false); }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  async function enact() {
    if (!stf?.resolution_id) return;
    setEnacting(true); setEnactResult(null);
    try {
      const res = await api.post(`/stf/${id}/resolutions`, {
        resolution_id: stf.resolution_id,
        confirmation: "ENACT",
      });
      const data = res.data as { state: string; resolution_ref: string; contested_reason?: string };
      if (data.state === "enacted" || data.state === "enacted_locked") {
        setEnactResult(`✓ ${data.resolution_ref} enacted`);
      } else {
        setEnactResult(`Contested: ${data.contested_reason ?? "engine not running"}`);
      }
      load();
    } catch (ex: unknown) {
      const msg = (ex as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Enactment failed";
      setEnactResult(`Error: ${msg}`);
    } finally { setEnacting(false); }
  }

  if (loading) return (
    <div className="space-y-4">
      {[1, 2].map(i => (
        <div key={i} className="card p-5 animate-pulse">
          <div className="h-3 bg-[var(--surface-raised)] rounded w-1/3 mb-3" />
          <div className="h-2 bg-[var(--surface-raised)] rounded w-full" />
        </div>
      ))}
    </div>
  );

  if (err || !stf) return (
    <div className="text-center py-16">
      <p className="text-sm font-mono text-[var(--text-muted)]">{err ?? "Not found"}</p>
      <Link href="/org/stf" className="text-xs text-[var(--gold)] hover:underline mt-2 block">
        ← STFs
      </Link>
    </div>
  );

  const typeColour = STF_TYPE_COLOUR[stf.stf_type] ?? "var(--text-muted)";
  const isBlind = BLIND_TYPES.has(stf.stf_type);
  const isCompleted = stf.state === "completed";
  const canEnact = isCompleted && stf.resolution_id &&
    aggregate?.majority_verdict === "approve";
  const progress = stf.assignment_count > 0
    ? Math.round((stf.verdicts_filed / stf.assignment_count) * 100)
    : 0;
  const overdue = stf.deadline && !isCompleted && new Date(stf.deadline) < new Date();

  return (
    <div className="space-y-5">
      <Link href="/org/stf"
        className="inline-flex items-center gap-1.5 text-xs font-mono
          text-[var(--text-muted)] hover:text-[var(--text)] transition-colors">
        <ChevronLeft size={12} /> STFs
      </Link>

      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start gap-4 mb-4">
          <div className="w-10 h-10 rounded-lg border flex items-center justify-center shrink-0"
            style={{ borderColor: typeColour + "40", background: typeColour + "15" }}>
            <Shield size={18} style={{ color: typeColour }} />
          </div>
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <span className="text-xs font-mono uppercase tracking-wider"
                style={{ color: typeColour }}>
                {stf.stf_type.toUpperCase()}
              </span>
              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                isCompleted
                  ? "text-emerald-400 border-emerald-800/40 bg-emerald-900/20"
                  : stf.state === "forming"
                  ? "text-blue-400 border-blue-800/40 bg-blue-900/20"
                  : "text-amber-400 border-amber-800/40 bg-amber-900/20"
              }`}>
                {stf.state}
              </span>
              {isBlind && (
                <span className="text-[10px] font-mono text-[var(--text-dim)] px-1.5 py-0.5
                  rounded border border-[var(--border)]">
                  Blind review
                </span>
              )}
            </div>
            <p className="text-sm text-[var(--text)] leading-relaxed">{stf.mandate}</p>
          </div>
        </div>

        {/* Progress */}
        <div className="mb-4">
          <div className="flex items-center justify-between text-[10px] font-mono
            text-[var(--text-muted)] mb-1.5">
            <span>{stf.verdicts_filed} of {stf.assignment_count} verdicts filed</span>
            <span>{progress}%</span>
          </div>
          <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
            <div className="h-full bg-[var(--gold)] rounded-full transition-all"
              style={{ width: `${progress}%` }} />
          </div>
        </div>

        {/* Meta grid */}
        <div className="grid grid-cols-2 gap-3 text-[10px] font-mono text-[var(--text-muted)]
          pt-3 border-t border-[var(--border)]">
          {stf.commissioned_by_circle && (
            <div>
              <span className="text-[var(--text-dim)]">Commissioned by</span>
              <p className="text-[var(--text)] mt-0.5">{stf.commissioned_by_circle.name}</p>
            </div>
          )}
          {stf.deadline && (
            <div>
              <span className="text-[var(--text-dim)]">Deadline</span>
              <p className={`mt-0.5 ${overdue ? "text-red-400" : "text-[var(--text)]"}`}>
                {new Date(stf.deadline).toLocaleDateString("en-GB", {
                  day: "numeric", month: "short", year: "numeric",
                })}
                {overdue && " (overdue)"}
              </p>
            </div>
          )}
          {stf.motion_id && (
            <div>
              <span className="text-[var(--text-dim)]">Motion</span>
              <Link href={`/org/motions/${stf.motion_id}`}
                className="text-[var(--gold)] hover:underline block mt-0.5">
                View motion →
              </Link>
            </div>
          )}
          {stf.completed_at && (
            <div>
              <span className="text-[var(--text-dim)]">Completed</span>
              <p className="text-[var(--text)] mt-0.5">
                {new Date(stf.completed_at).toLocaleDateString("en-GB", {
                  day: "numeric", month: "short", year: "numeric",
                })}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Aggregate verdict */}
      {aggregate && aggregate.verdicts_filed > 0 && (
        <div className="card p-5">
          <p className="section-label mb-3">Verdict aggregate</p>
          <VerdictBar counts={aggregate.counts} total={aggregate.verdicts_filed} />
          <div className="flex flex-wrap gap-2 mt-3">
            {Object.entries(aggregate.counts).map(([v, count]) => (
              <span key={v}
                className={`text-xs font-mono px-2 py-1 rounded bg-[var(--surface-raised)]
                  border border-[var(--border)] ${VERDICT_COLOUR[v] ?? "text-[var(--text)]"}`}>
                {v}: {count}
              </span>
            ))}
          </div>
          {aggregate.majority_verdict && (
            <div className="mt-3 pt-3 border-t border-[var(--border)] flex items-center gap-2">
              {aggregate.majority_verdict === "approve" || aggregate.majority_verdict === "clear"
                ? <CheckCircle size={14} className="text-emerald-400" />
                : <AlertCircle size={14} className="text-amber-400" />
              }
              <span className={`text-sm font-mono font-medium
                ${VERDICT_COLOUR[aggregate.majority_verdict] ?? "text-[var(--text)]"}`}>
                Majority: {aggregate.majority_verdict}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Enact button */}
      {canEnact && (
        <div className="card p-5 border-emerald-800/40 bg-emerald-900/10">
          <p className="section-label mb-2 text-emerald-400">Ready to enact</p>
          <p className="text-xs text-[var(--text-muted)] mb-3">
            All verdicts filed with approve majority. This will trigger the Integrity Engine
            atomic transaction.
          </p>
          {enactResult && (
            <div className={`text-xs font-mono mb-3 px-3 py-2 rounded border ${
              enactResult.startsWith("✓")
                ? "text-emerald-400 bg-emerald-900/20 border-emerald-800/40"
                : "text-red-400 bg-red-900/20 border-red-800/40"
            }`}>
              {enactResult}
            </div>
          )}
          <button onClick={enact} disabled={enacting}
            className="btn btn-primary text-xs gap-1.5 disabled:opacity-40">
            <CheckCircle size={12} />
            {enacting ? "Enacting…" : "Enact resolution"}
          </button>
        </div>
      )}

      {/* Assignments */}
      <div className="card p-5">
        <p className="section-label mb-3">
          Assignments
          {isBlind && (
            <span className="ml-2 text-[var(--text-dim)] normal-case font-body">
              — reviewer identities sealed
            </span>
          )}
        </p>
        {assignments.length === 0 ? (
          <div className="text-center py-6">
            <Clock size={20} className="mx-auto mb-2 text-[var(--text-dim)]" />
            <p className="text-xs font-mono text-[var(--text-muted)]">
              No assignments yet — Inferential Engine is matching candidates
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {assignments.map((a, i) => (
              <div key={a.id}
                className="flex items-center justify-between p-3 rounded
                  bg-[var(--surface-raised)] border border-[var(--border)]">
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-full border flex items-center
                    justify-center text-[10px] font-mono"
                    style={{
                      borderColor: typeColour + "40",
                      background: typeColour + "15",
                      color: typeColour,
                    }}>
                    {isBlind ? "?" : (a.member?.handle?.[0] ?? "?")}
                  </div>
                  <div>
                    <p className="text-xs font-mono text-[var(--text)]">
                      {isBlind
                        ? `Reviewer ${i + 1} — identity sealed`
                        : (a.member?.handle ?? "—")
                      }
                    </p>
                    <p className="text-[10px] font-mono text-[var(--text-dim)]">
                      {a.slot_type}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {a.verdict_filed_at ? (
                    <span className="flex items-center gap-1 text-[10px] font-mono
                      text-emerald-400">
                      <CheckCircle size={10} /> Filed
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[10px] font-mono
                      text-[var(--text-dim)]">
                      <Clock size={10} /> Pending
                    </span>
                  )}
                  {/* Review link — only for blind types with token-based access */}
                  {isBlind && !a.verdict_filed_at && (
                    <Link href={`/org/stf/${id}/review`}
                      className="text-[9px] font-mono text-[var(--gold)] hover:underline
                        px-1.5 py-0.5 border border-[var(--gold)]/30 rounded">
                      Review →
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
