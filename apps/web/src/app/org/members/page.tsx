"use client";

import { useEffect, useState } from "react";
import { membersApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

interface FeedItem {
  id: string;
  item_type: string;
  title: string;
  preview: string;
  relevance_score: number;
  dormain_ids: string[];
  created_at: string;
  ref_id: string;
}

export default function MembersPage() {
  const member = useAuthStore((s) => s.member);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    membersApi.feed()
      .then((r) => {
        const items = r.data?.items ?? r.data ?? [];
        setFeed(Array.isArray(items) ? items : []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (!member) return null;

  return (
    <div className="space-y-6">
      {/* Profile header */}
      <div className="card p-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-full bg-orbsys-surface-raised border border-orbsys-border flex items-center justify-center">
            <span className="font-mono text-lg text-orbsys-muted uppercase">
              {member.handle[0]}
            </span>
          </div>
          <div>
            <h1 className="font-display text-xl text-orbsys-text">
              {member.display_name}
            </h1>
            <p className="font-mono text-sm text-orbsys-muted">
              @{member.handle}
            </p>
            <p
              className={`font-mono text-xs mt-1 capitalize ${
                member.current_state === "active"
                  ? "text-emerald-400"
                  : member.current_state === "probationary"
                  ? "text-yellow-400"
                  : "text-orbsys-muted"
              }`}
            >
              {member.current_state}
            </p>
          </div>
        </div>
      </div>

      {/* Feed */}
      <div>
        <p className="section-label mb-3">Activity feed</p>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card p-4 animate-pulse">
                <div className="h-3 bg-orbsys-surface rounded w-2/3 mb-2" />
                <div className="h-2 bg-orbsys-surface rounded w-full" />
              </div>
            ))}
          </div>
        ) : feed.length === 0 ? (
          <div className="card p-6 text-center">
            <p className="text-sm font-mono text-orbsys-muted">
              No feed items yet. Participate in Commons to see relevant
              activity here.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {feed.map((item) => (
              <div key={item.id} className="card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="text-[10px] font-mono text-orbsys-muted uppercase tracking-wider">
                      {item.item_type}
                    </span>
                    <p className="text-sm text-orbsys-text mt-0.5">{item.title}</p>
                    {item.preview && (
                      <p className="text-xs text-orbsys-muted mt-0.5 line-clamp-1">
                        {item.preview}
                      </p>
                    )}
                  </div>
                  <span className="text-[10px] font-mono text-orbsys-muted shrink-0">
                    {new Date(item.created_at).toLocaleDateString("en-GB", {
                      day: "numeric", month: "short",
                    })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
