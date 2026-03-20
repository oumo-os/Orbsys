"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { FileText } from "lucide-react";

interface Motion {
  id: string;
  motion_type: string;
  state: string;
  filed_by: { id: string; handle: string } | null;
  cell_id: string;
  resolution: { resolution_ref: string; state: string } | null;
  created_at: string;
}

const STATE_COLOUR: Record<string, string> = {
  draft:                  "text-zinc-400",
  active:                 "text-blue-400",
  gate1_pending:          "text-amber-400",
  gate1_approved:         "text-emerald-400",
  gate1_rejected:         "text-red-400",
  pending_implementation: "text-blue-400",
  enacted:                "text-emerald-400",
  enacted_locked:         "text-emerald-400",
  contested:              "text-red-400",
  abandoned:              "text-zinc-500",
};

export default function MotionsPage() {
  const [motions, setMotions] = useState<Motion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/motions", { params: { page: 1, page_size: 50 } })
      .then(r => {
        const d = r.data;
        setMotions(Array.isArray(d) ? d : (d?.items ?? []));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-lg text-[var(--text)]">Motions</h1>
        <p className="text-xs text-[var(--text-muted)] font-mono mt-0.5">
          Filed governance proposals
        </p>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="card p-4 animate-pulse">
              <div className="h-3 bg-[var(--surface-raised)] rounded w-1/4 mb-2" />
              <div className="h-2 bg-[var(--surface-raised)] rounded w-3/4" />
            </div>
          ))}
        </div>
      ) : motions.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText size={32} className="text-[var(--text-dim)] mx-auto mb-3" />
          <p className="text-sm font-mono text-[var(--text-muted)]">
            Motions are filed from within a Cell after deliberation and crystallisation.
          </p>
          <Link href="/org/cells"
            className="text-xs text-[var(--gold)] hover:underline mt-2 block">
            Go to Cells →
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {motions.map(m => {
            const stateColour = STATE_COLOUR[m.state] ?? "text-zinc-400";
            return (
              <Link key={m.id} href={`/org/motions/${m.id}`}
                className="card p-4 block hover:border-[var(--gold)]/40 transition-colors group">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {m.resolution && (
                        <span className="text-[10px] font-mono text-[var(--gold)]">
                          {m.resolution.resolution_ref}
                        </span>
                      )}
                      <span className="text-[9px] font-mono text-[var(--text-dim)]">
                        {m.motion_type.replace("_", "-")}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-mono ${stateColour}`}>
                        {m.state.replace("_", " ")}
                      </span>
                      {m.filed_by && (
                        <span className="text-[10px] font-mono text-[var(--text-dim)]">
                          · @{m.filed_by.handle}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Link href={`/org/cells/${m.cell_id}`}
                      className="text-[9px] font-mono text-[var(--text-dim)]
                        hover:text-[var(--gold)] transition-colors"
                      onClick={e => e.stopPropagation()}>
                      Cell →
                    </Link>
                    <span className="text-[10px] font-mono text-[var(--text-dim)]">
                      {new Date(m.created_at).toLocaleDateString("en-GB", {
                        day: "numeric", month: "short",
                      })}
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
