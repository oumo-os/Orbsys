"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Layers, Clock, Users } from "lucide-react";

interface Cell {
  id: string;
  cell_type: string;
  state: string;
  founding_mandate: string | null;
  initiating_member: { id: string; handle: string } | null;
  invited_circles: { id: string; name: string }[];
  created_at: string;
  state_changed_at: string;
}

interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

const STATE_COLOUR: Record<string, string> = {
  active:              "text-emerald-400 border-emerald-800/40 bg-emerald-900/20",
  temporarily_closed:  "text-amber-400 border-amber-800/40 bg-amber-900/20",
  archived:            "text-zinc-400 border-zinc-700 bg-zinc-800/40",
  dissolved:           "text-zinc-500 border-zinc-700 bg-zinc-800/20",
  suspended:           "text-red-400 border-red-800/40 bg-red-900/20",
};

function rel(iso: string) {
  const d = Date.now() - new Date(iso).getTime();
  const h = Math.floor(d / 3600000);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function CellsPage() {
  const [cells, setCells] = useState<Cell[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  useEffect(() => {
    setLoading(true);
    api.get("/cells", { params: { page, page_size: 25 } })
      .then(r => {
        const data = r.data as Paginated<Cell> | Cell[];
        if (Array.isArray(data)) {
          setCells(data);
          setTotal(data.length);
        } else {
          setCells(data.items ?? []);
          setTotal(data.total ?? 0);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-lg text-[var(--text)]">Cells</h1>
        <p className="text-xs text-[var(--text-muted)] font-mono mt-0.5">
          Bounded deliberation spaces
        </p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-3 bg-[var(--surface-raised)] rounded w-1/3 mb-2" />
              <div className="h-2 bg-[var(--surface-raised)] rounded w-3/4" />
            </div>
          ))}
        </div>
      ) : cells.length === 0 ? (
        <div className="card p-12 text-center">
          <Layers size={32} className="text-[var(--text-dim)] mx-auto mb-3" />
          <p className="text-sm font-mono text-[var(--text-muted)]">
            Cells are created when a Commons thread is sponsored for deliberation.
          </p>
          <Link href="/org/commons"
            className="text-xs text-[var(--gold)] hover:underline mt-2 block">
            Go to Commons →
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {cells.map(c => {
            const stateClass = STATE_COLOUR[c.state] ?? STATE_COLOUR.active;
            return (
              <Link key={c.id} href={`/org/cells/${c.id}`}
                className="card p-5 block hover:border-[var(--gold)]/40 transition-colors group">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[9px] font-mono uppercase tracking-widest
                        text-[var(--text-dim)]">
                        {c.cell_type}
                      </span>
                      <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded
                        border ${stateClass}`}>
                        {c.state}
                      </span>
                    </div>
                    <p className="text-sm text-[var(--text)] group-hover:text-[var(--gold)]
                      transition-colors line-clamp-2">
                      {c.founding_mandate ?? "No mandate set"}
                    </p>
                    {c.invited_circles.length > 0 && (
                      <div className="flex items-center gap-1.5 mt-2">
                        <Users size={10} className="text-[var(--text-dim)]" />
                        <div className="flex flex-wrap gap-1">
                          {c.invited_circles.slice(0, 3).map(circle => (
                            <span key={circle.id}
                              className="text-[10px] font-mono text-[var(--text-muted)]">
                              {circle.name}
                            </span>
                          ))}
                          {c.invited_circles.length > 3 && (
                            <span className="text-[10px] font-mono text-[var(--text-dim)]">
                              +{c.invited_circles.length - 3}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1 text-[10px] font-mono
                    text-[var(--text-dim)] shrink-0">
                    <Clock size={10} />
                    {rel(c.created_at)}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {total > 25 && (
        <div className="flex items-center justify-between text-xs font-mono
          text-[var(--text-muted)]">
          <span>{(page - 1) * 25 + 1}–{Math.min(page * 25, total)} of {total}</span>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="btn btn-ghost py-1 px-3 disabled:opacity-40">← Prev</button>
            <button onClick={() => setPage(p => p + 1)} disabled={page * 25 >= total}
              className="btn btn-ghost py-1 px-3 disabled:opacity-40">Next →</button>
          </div>
        </div>
      )}
    </div>
  );
}
