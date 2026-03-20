"use client";

import Link from "next/link";

import { useEffect, useState } from "react";
import { stfApi } from "@/lib/api";
import { Shield } from "lucide-react";

interface STFSummary {
  id: string;
  stf_type: string;
  state: string;
  mandate_preview: string;
  deadline: string | null;
  assignment_count: number;
  verdicts_filed: number;
  created_at: string;
}

const STATE_BADGE: Record<string, string> = {
  forming:   "text-blue-400 border-blue-800/40 bg-blue-900/20",
  active:    "text-emerald-400 border-emerald-800/40 bg-emerald-900/20",
  deliberating: "text-yellow-400 border-yellow-800/40 bg-yellow-900/20",
  completed: "text-zinc-400 border-zinc-700 bg-zinc-800",
};

export default function STFPage() {
  const [data, setData] = useState<{ items: STFSummary[]; total: number } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    stfApi.list({ page: 1, page_size: 50 })
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-lg text-orbsys-text">
          Structured Task Forces
        </h1>
        <p className="text-xs text-orbsys-muted font-mono mt-0.5">
          Competence-weighted audit panels
        </p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-3 bg-orbsys-surface rounded w-1/4 mb-2" />
              <div className="h-2 bg-orbsys-surface rounded w-3/4" />
            </div>
          ))}
        </div>
      ) : !data || data.items.length === 0 ? (
        <div className="card p-8 text-center">
          <Shield size={24} className="text-orbsys-muted mx-auto mb-2" />
          <p className="text-sm font-mono text-orbsys-muted">
            No STF instances yet.
          </p>
          <p className="text-xs text-orbsys-muted mt-1">
            STFs are commissioned automatically when motions are filed.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.items.map((stf) => {
            const badgeClass = STATE_BADGE[stf.state] ?? STATE_BADGE.completed;
            const progress =
              stf.assignment_count > 0
                ? Math.round((stf.verdicts_filed / stf.assignment_count) * 100)
                : 0;

            return (
              <Link key={stf.id} href={`/org/stf/${stf.id}`} className="card p-5 block hover:border-[var(--gold)]/40 transition-colors group">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-mono uppercase tracking-widest text-orbsys-muted">
                        {stf.stf_type}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${badgeClass}`}
                      >
                        {stf.state}
                      </span>
                    </div>
                    <p className="text-sm text-orbsys-text line-clamp-2">
                      {stf.mandate_preview}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-[10px] font-mono text-orbsys-muted">
                  <span>{stf.verdicts_filed}/{stf.assignment_count} verdicts</span>
                  {stf.assignment_count > 0 && (
                    <div className="flex items-center gap-1.5 flex-1">
                      <div className="flex-1 h-1 bg-orbsys-surface rounded-full overflow-hidden">
                        <div
                          className="h-full bg-orbsys-gold/60 rounded-full"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                      <span>{progress}%</span>
                    </div>
                  )}
                  {stf.deadline && (
                    <span className={
                      new Date(stf.deadline) < new Date()
                        ? "text-red-400" : ""
                    }>
                      Due{" "}
                      {new Date(stf.deadline).toLocaleDateString("en-GB", {
                        day: "numeric", month: "short",
                      })}
                    </span>
                  )}
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
