"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { circlesApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { ChevronLeft, Users, Circle, CheckCircle, AlertCircle, Clock } from "lucide-react";

interface Member { id: string; handle: string; display_name: string }
interface DormainRef { id: string; name: string }

interface CircleDormain {
  dormain: DormainRef;
  mandate_type: string;  // primary | secondary
  added_at: string;
  removed_at: string | null;
}

interface CircleMember {
  member: Member;
  joined_at: string;
  current_state: string;
  primary_dormain_ws: number | null;
}

interface CircleHealth {
  circle_id: string;
  circle_name: string;
  snapshot_at: string | null;
  overall_verdict: string | null;
  active_member_count: number;
  median_ws_primary_dormain: number | null;
  participation_rate_90d: number | null;
  open_concerns: string[];
  stf_instance_id: string | null;
}

interface CircleDetail {
  id: string;
  org_id: string;
  name: string;
  description: string | null;
  tenets: string | null;
  founding_circle: boolean;
  dormains: CircleDormain[];
  member_count: number;
  created_at: string;
  dissolved_at: string | null;
}

const STATE_COLOUR: Record<string, string> = {
  active:       "text-emerald-400",
  probationary: "text-amber-400",
  on_leave:     "text-blue-400",
  inactive:     "text-zinc-500",
  suspended:    "text-red-400",
};

export default function CircleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const currentMember = useAuthStore(s => s.member);

  const [circle, setCircle]   = useState<CircleDetail | null>(null);
  const [members, setMembers] = useState<CircleMember[]>([]);
  const [health, setHealth]   = useState<CircleHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr]         = useState<string | null>(null);
  const [tab, setTab]         = useState<"members" | "health">("members");

  const load = useCallback(async () => {
    try {
      const [circleRes, membersRes, healthRes] = await Promise.all([
        circlesApi.get(id),
        circlesApi.members(id),
        circlesApi.health(id).catch(() => ({ data: null })),
      ]);
      setCircle(circleRes.data as CircleDetail);
      setMembers((membersRes.data ?? []) as CircleMember[]);
      setHealth(healthRes.data as CircleHealth | null);
    } catch {
      setErr("Circle not found.");
    } finally { setLoading(false); }
  }, [id]);

  useEffect(() => { load(); }, [load]);

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

  if (err || !circle) return (
    <div className="text-center py-16">
      <p className="text-sm font-mono text-[var(--text-muted)]">{err ?? "Not found"}</p>
      <Link href="/org/circles"
        className="text-xs text-[var(--gold)] hover:underline mt-2 block">
        ← Circles
      </Link>
    </div>
  );

  const isMember = members.some(m => m.member.id === currentMember?.id);
  const primaryDormains  = circle.dormains.filter(d => d.mandate_type === "primary" && !d.removed_at);
  const secondaryDormains = circle.dormains.filter(d => d.mandate_type === "secondary" && !d.removed_at);

  return (
    <div className="space-y-5">
      <Link href="/org/circles"
        className="inline-flex items-center gap-1.5 text-xs font-mono
          text-[var(--text-muted)] hover:text-[var(--text)] transition-colors">
        <ChevronLeft size={12} /> Circles
      </Link>

      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start gap-4 mb-4">
          <div className="w-10 h-10 rounded-lg bg-[var(--gold-glow)] border
            border-[var(--gold)]/30 flex items-center justify-center shrink-0">
            <Circle size={18} className="text-[var(--gold)]" />
          </div>
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <h1 className="font-display text-xl text-[var(--text)]">{circle.name}</h1>
              {circle.founding_circle && (
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded
                  border border-[var(--gold)]/30 text-[var(--gold)]">
                  Founding
                </span>
              )}
              {circle.dissolved_at && (
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded
                  border border-red-800/40 text-red-400">
                  Dissolved
                </span>
              )}
              {isMember && (
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded
                  border border-emerald-800/40 text-emerald-400 bg-emerald-900/20">
                  Member
                </span>
              )}
            </div>
            {circle.description && (
              <p className="text-sm text-[var(--text)] leading-relaxed">{circle.description}</p>
            )}
          </div>
          <div className="flex items-center gap-1.5 text-sm font-mono text-[var(--text-muted)]
            shrink-0">
            <Users size={13} />
            {circle.member_count}
          </div>
        </div>

        {/* Tenets */}
        {circle.tenets && (
          <div className="mb-4 p-3 rounded bg-[var(--gold-glow)] border border-[var(--gold)]/20">
            <p className="text-[9px] font-mono uppercase tracking-wider text-[var(--gold)] mb-1">
              Tenets
            </p>
            <p className="text-sm text-[var(--text)] leading-relaxed">{circle.tenets}</p>
          </div>
        )}

        {/* Dormain mandates */}
        {(primaryDormains.length > 0 || secondaryDormains.length > 0) && (
          <div className="pt-3 border-t border-[var(--border)]">
            <p className="text-[9px] font-mono uppercase tracking-wider
              text-[var(--text-dim)] mb-2">
              Mandate Dormains
            </p>
            <div className="flex flex-wrap gap-2">
              {primaryDormains.map(d => (
                <span key={d.dormain.id}
                  className="text-xs font-mono px-2 py-1 rounded
                    bg-[var(--gold-glow)] border border-[var(--gold)]/30
                    text-[var(--gold)]">
                  {d.dormain.name}
                  <span className="text-[9px] ml-1 opacity-60">primary</span>
                </span>
              ))}
              {secondaryDormains.map(d => (
                <span key={d.dormain.id}
                  className="text-xs font-mono px-2 py-1 rounded
                    bg-[var(--surface-raised)] border border-[var(--border)]
                    text-[var(--text-muted)]">
                  {d.dormain.name}
                  <span className="text-[9px] ml-1 opacity-60">secondary</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[var(--border)]">
        {[
          { key: "members", label: `Members (${members.length})` },
          { key: "health",  label: "Health" },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key as "members" | "health")}
            className={`px-4 py-2.5 text-xs font-mono transition-colors border-b-2 -mb-px ${
              tab === t.key
                ? "text-[var(--gold)] border-[var(--gold)]"
                : "text-[var(--text-muted)] border-transparent hover:text-[var(--text)]"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Members tab */}
      {tab === "members" && (
        <div className="space-y-2">
          {members.length === 0 ? (
            <div className="card p-8 text-center">
              <Users size={24} className="mx-auto mb-2 text-[var(--text-dim)]" />
              <p className="text-sm font-mono text-[var(--text-muted)]">No active members.</p>
            </div>
          ) : (
            members.map(m => (
              <div key={m.member.id}
                className="card p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-[var(--surface-raised)]
                    border border-[var(--border)] flex items-center justify-center">
                    <span className="text-[11px] font-mono text-[var(--text-muted)] uppercase">
                      {m.member.handle[0]}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm font-mono text-[var(--text)]">
                      {m.member.display_name}
                    </p>
                    <p className="text-[10px] font-mono text-[var(--text-dim)]">
                      @{m.member.handle}
                      {m.member.id === currentMember?.id && (
                        <span className="ml-2 text-[var(--gold)]">you</span>
                      )}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {m.primary_dormain_ws !== null && (
                    <div className="text-right">
                      <p className="text-sm font-mono text-[var(--gold)]">
                        {m.primary_dormain_ws.toFixed(0)}
                      </p>
                      <p className="text-[9px] font-mono text-[var(--text-dim)]">W_s</p>
                    </div>
                  )}
                  <span className={`text-[10px] font-mono capitalize
                    ${STATE_COLOUR[m.current_state] ?? "text-zinc-400"}`}>
                    {m.current_state}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Health tab */}
      {tab === "health" && (
        <div>
          {!health || !health.snapshot_at ? (
            <div className="card p-8 text-center">
              <Clock size={24} className="mx-auto mb-2 text-[var(--text-dim)]" />
              <p className="text-sm font-mono text-[var(--text-muted)]">
                No health snapshot yet.
              </p>
              <p className="text-xs text-[var(--text-dim)] mt-1">
                Health is assessed by the periodic aSTF cycle.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Overall */}
              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <p className="section-label">Overall</p>
                  {health.overall_verdict && (
                    <div className={`flex items-center gap-1.5 text-xs font-mono ${
                      health.overall_verdict === "healthy"
                        ? "text-emerald-400" : "text-amber-400"
                    }`}>
                      {health.overall_verdict === "healthy"
                        ? <CheckCircle size={12} />
                        : <AlertCircle size={12} />
                      }
                      {health.overall_verdict}
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-4 text-xs font-mono">
                  <div>
                    <p className="text-[var(--text-dim)]">Active members</p>
                    <p className="text-[var(--text)] text-lg font-medium mt-0.5">
                      {health.active_member_count}
                    </p>
                  </div>
                  {health.median_ws_primary_dormain !== null && (
                    <div>
                      <p className="text-[var(--text-dim)]">Median W_s</p>
                      <p className="text-[var(--gold)] text-lg font-medium mt-0.5">
                        {health.median_ws_primary_dormain.toFixed(0)}
                      </p>
                    </div>
                  )}
                  {health.participation_rate_90d !== null && (
                    <div>
                      <p className="text-[var(--text-dim)]">90d participation</p>
                      <p className="text-[var(--text)] text-lg font-medium mt-0.5">
                        {(health.participation_rate_90d * 100).toFixed(0)}%
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Open concerns */}
              {health.open_concerns.length > 0 && (
                <div className="card p-5">
                  <p className="section-label mb-3">Open concerns</p>
                  <ul className="space-y-2">
                    {health.open_concerns.map((c, i) => (
                      <li key={i} className="flex gap-2 text-sm">
                        <AlertCircle size={13} className="text-amber-400 shrink-0 mt-0.5" />
                        <span className="text-[var(--text)]">{c}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="text-[10px] font-mono text-[var(--text-dim)] text-center">
                Snapshot from{" "}
                {new Date(health.snapshot_at).toLocaleDateString("en-GB", {
                  day: "numeric", month: "long", year: "numeric",
                })}
                {health.stf_instance_id && (
                  <>
                    {" · "}
                    <Link href={`/org/stf/${health.stf_instance_id}`}
                      className="text-[var(--gold)] hover:underline">
                      View aSTF →
                    </Link>
                  </>
                )}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
