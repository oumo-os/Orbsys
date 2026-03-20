"use client";

import Link from "next/link";

import { useEffect, useState } from "react";
import { circlesApi } from "@/lib/api";
import { Users } from "lucide-react";

interface CircleSummary {
  id: string;
  name: string;
  description: string | null;
  dormains: { id: string; name: string }[];
  member_count: number;
  dissolved_at: string | null;
}

export default function CirclesPage() {
  const [circles, setCircles] = useState<CircleSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    circlesApi.list()
      .then((r) => setCircles(r.data ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-lg text-orbsys-text">Circles</h1>
        <p className="text-xs text-orbsys-muted font-mono mt-0.5">
          Membership and mandate structures
        </p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-3 bg-orbsys-surface rounded w-1/4 mb-2" />
              <div className="h-2 bg-orbsys-surface rounded w-2/3" />
            </div>
          ))}
        </div>
      ) : circles.length === 0 ? (
        <div className="card p-8 text-center">
          <p className="text-sm font-mono text-orbsys-muted">
            No active circles.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {circles.map((c) => (
            <Link
              key={c.id}
              href={`/org/circles/${c.id}`}
              className={`card p-5 block hover:border-[var(--gold)]/40 transition-colors ${c.dissolved_at ? "opacity-50" : ""}`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-sm font-medium text-orbsys-text">
                    {c.name}
                  </h2>
                  {c.description && (
                    <p className="text-xs text-orbsys-muted mt-0.5 line-clamp-1">
                      {c.description}
                    </p>
                  )}
                  {c.dormains.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {c.dormains.map((d) => (
                        <span
                          key={d.id}
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-orbsys-surface border border-orbsys-border text-orbsys-muted"
                        >
                          {d.name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1 text-xs font-mono text-orbsys-muted">
                  <Users size={11} />
                  {c.member_count}
                </div>
              </div>
              {c.dissolved_at && (
                <p className="text-[10px] font-mono text-red-400 mt-2">
                  Dissolved{" "}
                  {new Date(c.dissolved_at).toLocaleDateString("en-GB", {
                    day: "numeric", month: "short", year: "numeric",
                  })}
                </p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
