"use client";

import { useEffect, useState } from "react";
import { membersApi, api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

interface FeedItem {
  id: string;
  item_type: string;
  title: string;
  preview: string;
  relevance_score: number;
  created_at: string;
}

interface Application {
  id: string;
  handle: string;
  display_name: string;
  email: string;
  motivation: string | null;
  expertise_summary: string | null;
  status: string;
  created_at: string;
}

export default function MembersPage() {
  const member = useAuthStore((s) => s.member);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [tab, setTab] = useState<"feed" | "applications">("feed");
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState<string | null>(null);

  useEffect(() => {
    membersApi.feed()
      .then((r) => setFeed(r.data?.items ?? r.data ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (tab === "applications") {
      api.get("/members/applications?status=pending")
        .then((r) => setApplications(r.data?.items ?? []))
        .catch(() => {});
    }
  }, [tab]);

  async function reviewApplication(appId: string, approve: boolean) {
    setReviewing(appId);
    try {
      await api.post(`/members/applications/${appId}/review`, {
        approve,
        note: approve ? "Approved by Membership Circle." : "Application declined.",
      });
      setApplications((prev) => prev.filter((a) => a.id !== appId));
    } catch {
      // silently swallow — member may not be in Membership Circle
    } finally {
      setReviewing(null);
    }
  }

  if (!member) return null;

  return (
    <div className="space-y-6">
      {/* Profile */}
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
              @{member.handle} · {member.current_state}
            </p>
          </div>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-orbsys-border">
        {(["feed", "applications"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs font-mono uppercase tracking-widest border-b-2 transition-colors ${
              tab === t
                ? "border-orbsys-gold text-orbsys-gold"
                : "border-transparent text-orbsys-muted hover:text-orbsys-text"
            }`}
          >
            {t === "applications" ? "Applications" : "Activity Feed"}
          </button>
        ))}
      </div>

      {/* Feed */}
      {tab === "feed" && (
        <div>
          {loading ? (
            <p className="font-mono text-sm text-orbsys-muted">Loading…</p>
          ) : feed.length === 0 ? (
            <p className="font-mono text-sm text-orbsys-muted">
              No activity yet. Post in Commons to start building your W_s.
            </p>
          ) : (
            <div className="space-y-2">
              {feed.map((item) => (
                <div key={item.id} className="card p-4">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-[10px] text-orbsys-muted uppercase tracking-wider">
                      {item.item_type}
                    </span>
                    <span className="font-mono text-[10px] text-orbsys-muted">
                      {new Date(item.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-sm text-orbsys-text-sub font-display">
                    {item.title || item.preview}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Applications review queue */}
      {tab === "applications" && (
        <div>
          <div className="mb-4">
            <p className="font-mono text-xs text-orbsys-muted">
              Membership applications · Membership Circle review queue
            </p>
          </div>

          {applications.length === 0 ? (
            <div className="card p-6 text-center">
              <p className="font-mono text-sm text-orbsys-muted">
                No pending applications.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {applications.map((app) => (
                <div key={app.id} className="card p-5 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-display text-orbsys-text">
                        {app.display_name}
                      </p>
                      <p className="font-mono text-xs text-orbsys-muted">
                        @{app.handle} · {app.email}
                      </p>
                    </div>
                    <span className="font-mono text-[10px] text-orbsys-muted">
                      {new Date(app.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  {app.motivation && (
                    <div>
                      <p className="font-mono text-[10px] text-orbsys-muted uppercase tracking-wider mb-1">
                        Motivation
                      </p>
                      <p className="text-sm text-orbsys-text-sub font-display leading-relaxed">
                        {app.motivation}
                      </p>
                    </div>
                  )}

                  {app.expertise_summary && (
                    <div>
                      <p className="font-mono text-[10px] text-orbsys-muted uppercase tracking-wider mb-1">
                        Expertise
                      </p>
                      <p className="text-sm text-orbsys-text-sub font-display leading-relaxed">
                        {app.expertise_summary}
                      </p>
                    </div>
                  )}

                  <div className="flex gap-2 pt-2 border-t border-orbsys-border">
                    <button
                      disabled={reviewing === app.id}
                      onClick={() => reviewApplication(app.id, true)}
                      className="px-4 py-1.5 rounded border border-orbsys-green/40 bg-orbsys-green/10
                                 text-orbsys-green font-mono text-xs hover:bg-orbsys-green/20
                                 disabled:opacity-50 transition-colors"
                    >
                      Approve
                    </button>
                    <button
                      disabled={reviewing === app.id}
                      onClick={() => reviewApplication(app.id, false)}
                      className="px-4 py-1.5 rounded border border-orbsys-border
                                 text-orbsys-muted font-mono text-xs hover:text-orbsys-text
                                 disabled:opacity-50 transition-colors"
                    >
                      Decline
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
