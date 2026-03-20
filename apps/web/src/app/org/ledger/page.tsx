"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { ledgerApi } from "@/lib/api";
import { Shield, CheckCircle, XCircle, RefreshCw, FileText } from "lucide-react";

interface LedgerEvent {
  id: string;
  org_id: string;
  event_type: string;
  subject_id: string | null;
  subject_type: string | null;
  payload: Record<string, unknown>;
  triggered_by_member: string | null;
  triggered_by_resolution: string | null;
  created_at: string;
  prev_hash: string;
  event_hash: string;
}

interface VerifyResult {
  status: "ok" | "broken";
  verified_events: number;
  first_broken_event_id: string | null;
  verified_at: string;
}

interface AuditRationale {
  slot_type: string;
  verdict: string;
  rationale: string | null;
  revision_directive: string | null;
}

interface AuditReport {
  stf_instance_id: string;
  stf_type: string;
  mandate: string;
  commissioned_by_circle_id: string | null;
  motion_id: string | null;
  majority_verdict: string;
  rationales: AuditRationale[];
  completed_at: string | null;
  ledger_event_id: string;
}

interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

// ── Event type grouping ───────────────────────────────────────────────────────

const EVENT_COLOURS: Record<string, string> = {
  // Governance lifecycle
  motion_filed:          "text-blue-400",
  motion_gate1_result:   "text-amber-400",
  resolution_enacted:    "text-emerald-400",
  resolution_contested:  "text-red-400",
  // Competence
  delta_c_applied:       "text-purple-400",
  wh_boost_applied:      "text-violet-400",
  // STF
  stf_commissioned:      "text-[var(--stf-astf)]",
  stf_assignment_created:"text-[var(--stf-xstf)]",
  stf_completed:         "text-emerald-400",
  // Anomaly
  anomaly_flag:          "text-red-400",
  // Default
  _default:              "text-[var(--text-muted)]",
};

const VERDICT_COLOUR: Record<string, string> = {
  approve: "text-emerald-400",
  clear:   "text-emerald-400",
  reject:  "text-red-400",
  revision_request: "text-amber-400",
  concerns: "text-amber-400",
};

function rel(iso: string) {
  const d = Date.now() - new Date(iso).getTime();
  const m = Math.floor(d / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function EventCard({ event }: { event: LedgerEvent }) {
  const [expanded, setExpanded] = useState(false);
  const colour = EVENT_COLOURS[event.event_type] ?? EVENT_COLOURS._default;

  return (
    <div className="border-b border-[var(--border)] last:border-0">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-0 py-3 flex items-start justify-between gap-4
          hover:bg-[var(--surface-raised)] transition-colors rounded"
      >
        <div className="flex items-start gap-3">
          <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
            style={{ background: "currentColor" }}
            className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${colour}`}
          />
          <div className="min-w-0">
            <p className={`text-xs font-mono font-medium ${colour}`}>
              {event.event_type}
            </p>
            {event.subject_type && event.subject_id && (
              <p className="text-[10px] font-mono text-[var(--text-dim)] mt-0.5">
                {event.subject_type} · {event.subject_id.slice(0, 8)}…
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-[9px] font-mono text-[var(--text-dim)]">
            {rel(event.created_at)}
          </span>
          <span className="text-[10px] text-[var(--text-dim)]">
            {expanded ? "▲" : "▼"}
          </span>
        </div>
      </button>

      {expanded && (
        <div className="pb-4 pl-4 space-y-3">
          {/* Hash chain */}
          <div className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--border)]">
            <p className="text-[9px] font-mono text-[var(--text-dim)] mb-1.5 uppercase tracking-wider">
              Hash chain
            </p>
            <div className="space-y-1 font-mono text-[10px]">
              <div className="flex gap-2">
                <span className="text-[var(--text-dim)] w-16 shrink-0">prev</span>
                <span className="text-[var(--text-muted)] break-all">{event.prev_hash.slice(0, 32)}…</span>
              </div>
              <div className="flex gap-2">
                <span className="text-[var(--text-dim)] w-16 shrink-0">hash</span>
                <span className="text-[var(--gold)] break-all">{event.event_hash.slice(0, 32)}…</span>
              </div>
            </div>
          </div>

          {/* Payload */}
          {Object.keys(event.payload).length > 0 && (
            <div>
              <p className="text-[9px] font-mono text-[var(--text-dim)] uppercase
                tracking-wider mb-1.5">Payload</p>
              <pre className="text-[10px] font-mono text-[var(--text-muted)]
                bg-[var(--surface-raised)] border border-[var(--border)]
                rounded p-3 overflow-auto max-h-40 whitespace-pre-wrap">
                {JSON.stringify(event.payload, null, 2)}
              </pre>
            </div>
          )}

          {/* Navigation links */}
          <div className="flex gap-3">
            {event.subject_type && event.subject_id && (
              <>
                {event.subject_type === "motion" && (
                  <Link href={`/org/motions/${event.subject_id}`}
                    className="text-[10px] font-mono text-[var(--gold)] hover:underline">
                    View motion →
                  </Link>
                )}
                {event.subject_type === "stf_instance" && (
                  <Link href={`/org/stf/${event.subject_id}`}
                    className="text-[10px] font-mono text-[var(--gold)] hover:underline">
                    View STF →
                  </Link>
                )}
                {event.subject_type === "cell" && (
                  <Link href={`/org/cells/${event.subject_id}`}
                    className="text-[10px] font-mono text-[var(--gold)] hover:underline">
                    View cell →
                  </Link>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function LedgerPage() {
  const [events, setEvents] = useState<LedgerEvent[]>([]);
  const [eventsTotal, setEventsTotal] = useState(0);
  const [reports, setReports] = useState<AuditReport[]>([]);
  const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [tab, setTab] = useState<"events" | "audit">("events");
  const [page, setPage] = useState(1);
  const [eventTypeFilter, setEventTypeFilter] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const params: Record<string, unknown> = { page, page_size: 30 };
    if (eventTypeFilter) params.event_type = eventTypeFilter;
    try {
      const [evRes, archiveRes] = await Promise.all([
        ledgerApi.events(params),
        tab === "audit" ? ledgerApi.auditArchive({ page: 1, page_size: 20 }) : null,
      ]);
      const evData = evRes.data as Paginated<LedgerEvent>;
      setEvents(evData.items ?? []);
      setEventsTotal(evData.total ?? 0);
      if (archiveRes) {
        const archData = archiveRes.data as Paginated<AuditReport>;
        setReports(archData.items ?? []);
      }
    } catch {
      setEvents([]);
    } finally { setLoading(false); }
  }, [page, tab, eventTypeFilter]);

  useEffect(() => { load(); }, [load]);

  async function verify() {
    setVerifying(true);
    try {
      const res = await ledgerApi.verify();
      setVerifyResult(res.data as VerifyResult);
    } catch {
      setVerifyResult({ status: "broken", verified_events: 0,
        first_broken_event_id: null, verified_at: new Date().toISOString() });
    } finally { setVerifying(false); }
  }

  const EVENT_TYPE_OPTIONS = [
    "", "motion_filed", "motion_gate1_result", "resolution_enacted",
    "resolution_contested", "delta_c_applied", "stf_commissioned",
    "stf_completed", "anomaly_flag", "wh_boost_applied",
  ];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-lg text-[var(--text)]">Ledger</h1>
          <p className="text-xs text-[var(--text-muted)] font-mono mt-0.5">
            Tamper-evident governance record
          </p>
        </div>
        <button onClick={verify} disabled={verifying}
          className="btn btn-ghost text-xs gap-1.5 disabled:opacity-40">
          <RefreshCw size={11} className={verifying ? "animate-spin" : ""} />
          {verifying ? "Verifying…" : "Verify chain"}
        </button>
      </div>

      {/* Chain verification result */}
      {verifyResult && (
        <div className={`card p-4 flex items-start gap-3 ${
          verifyResult.status === "ok"
            ? "border-emerald-800/40 bg-emerald-900/10"
            : "border-red-800/40 bg-red-900/10"
        }`}>
          {verifyResult.status === "ok"
            ? <CheckCircle size={16} className="text-emerald-400 shrink-0 mt-0.5" />
            : <XCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
          }
          <div>
            <p className={`text-sm font-mono font-medium ${
              verifyResult.status === "ok" ? "text-emerald-400" : "text-red-400"
            }`}>
              {verifyResult.status === "ok"
                ? `Chain intact — ${verifyResult.verified_events.toLocaleString()} events verified`
                : `Chain broken at event ${verifyResult.first_broken_event_id?.slice(0, 8)}…`
              }
            </p>
            <p className="text-[10px] font-mono text-[var(--text-muted)] mt-0.5">
              Verified at{" "}
              {new Date(verifyResult.verified_at).toLocaleTimeString("en-GB", {
                hour: "2-digit", minute: "2-digit",
              })}
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[var(--border)]">
        {[
          { key: "events", label: `Events (${eventsTotal.toLocaleString()})` },
          { key: "audit",  label: "Audit archive" },
        ].map(t => (
          <button key={t.key}
            onClick={() => { setTab(t.key as "events" | "audit"); setPage(1); }}
            className={`px-4 py-2.5 text-xs font-mono transition-colors border-b-2 -mb-px ${
              tab === t.key
                ? "text-[var(--gold)] border-[var(--gold)]"
                : "text-[var(--text-muted)] border-transparent hover:text-[var(--text)]"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Events tab */}
      {tab === "events" && (
        <div>
          {/* Filter */}
          <div className="mb-4">
            <select value={eventTypeFilter}
              onChange={e => { setEventTypeFilter(e.target.value); setPage(1); }}
              className="bg-[var(--surface)] border border-[var(--border)] rounded
                px-3 py-1.5 text-xs font-mono text-[var(--text)]
                focus:outline-none focus:border-[var(--gold)]">
              <option value="">All event types</option>
              {EVENT_TYPE_OPTIONS.slice(1).map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div className="card p-4">
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="h-8 bg-[var(--surface-raised)] rounded animate-pulse" />
                ))}
              </div>
            ) : events.length === 0 ? (
              <div className="text-center py-8">
                <Shield size={24} className="mx-auto mb-2 text-[var(--text-dim)]" />
                <p className="text-sm font-mono text-[var(--text-muted)]">No events yet.</p>
              </div>
            ) : (
              <div>
                {events.map(e => <EventCard key={e.id} event={e} />)}
              </div>
            )}
          </div>

          {eventsTotal > 30 && (
            <div className="flex items-center justify-between text-xs font-mono
              text-[var(--text-muted)] mt-3">
              <span>{(page - 1) * 30 + 1}–{Math.min(page * 30, eventsTotal)} of {eventsTotal.toLocaleString()}</span>
              <div className="flex gap-2">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                  className="btn btn-ghost py-1 px-3 text-xs disabled:opacity-40">← Prev</button>
                <button onClick={() => setPage(p => p + 1)} disabled={page * 30 >= eventsTotal}
                  className="btn btn-ghost py-1 px-3 text-xs disabled:opacity-40">Next →</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Audit archive tab */}
      {tab === "audit" && (
        <div>
          {loading ? (
            <div className="space-y-3">
              {[1, 2].map(i => (
                <div key={i} className="card p-5 animate-pulse">
                  <div className="h-3 bg-[var(--surface-raised)] rounded w-1/3 mb-2" />
                  <div className="h-2 bg-[var(--surface-raised)] rounded w-full" />
                </div>
              ))}
            </div>
          ) : reports.length === 0 ? (
            <div className="card p-10 text-center">
              <FileText size={28} className="mx-auto mb-3 text-[var(--text-dim)]" />
              <p className="text-sm font-mono text-[var(--text-muted)]">
                No completed STF reports yet.
              </p>
              <p className="text-xs text-[var(--text-dim)] mt-1">
                Reports appear after an STF panel files all verdicts.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {reports.map(r => (
                <div key={r.stf_instance_id} className="card p-5">
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-mono uppercase tracking-wider"
                          style={{ color: `var(--stf-${r.stf_type === "astf_motion" ? "astf" : r.stf_type})` }}>
                          {r.stf_type.toUpperCase()}
                        </span>
                        <span className={`text-xs font-mono font-medium
                          ${VERDICT_COLOUR[r.majority_verdict] ?? "text-zinc-400"}`}>
                          {r.majority_verdict}
                        </span>
                      </div>
                      <p className="text-sm text-[var(--text)] line-clamp-2">{r.mandate}</p>
                    </div>
                    {r.motion_id && (
                      <Link href={`/org/motions/${r.motion_id}`}
                        className="text-[10px] font-mono text-[var(--gold)] hover:underline shrink-0">
                        Motion →
                      </Link>
                    )}
                  </div>

                  {r.rationales.length > 0 && (
                    <div className="space-y-2 pt-3 border-t border-[var(--border)]">
                      <p className="text-[9px] font-mono uppercase tracking-wider
                        text-[var(--text-dim)]">
                        Rationales (identity sealed)
                      </p>
                      {r.rationales.map((rat, i) => (
                        <div key={i}
                          className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--border)]">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-[9px] font-mono text-[var(--text-dim)]">
                              Reviewer {i + 1} · {rat.slot_type}
                            </span>
                            <span className={`text-[9px] font-mono
                              ${VERDICT_COLOUR[rat.verdict] ?? "text-zinc-400"}`}>
                              {rat.verdict}
                            </span>
                          </div>
                          {rat.rationale && (
                            <p className="text-xs text-[var(--text)] leading-relaxed">
                              {rat.rationale}
                            </p>
                          )}
                          {rat.revision_directive && (
                            <div className="mt-2 p-2 rounded bg-amber-900/20
                              border border-amber-800/40">
                              <p className="text-[10px] font-mono text-amber-400 mb-1">
                                Directive
                              </p>
                              <p className="text-xs text-amber-200">{rat.revision_directive}</p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {r.completed_at && (
                    <p className="text-[10px] font-mono text-[var(--text-dim)] mt-3">
                      Completed{" "}
                      {new Date(r.completed_at).toLocaleDateString("en-GB", {
                        day: "numeric", month: "short", year: "numeric",
                      })}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
