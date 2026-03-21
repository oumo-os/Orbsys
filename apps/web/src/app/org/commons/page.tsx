"use client";

import { useEffect, useState, useCallback, FormEvent } from "react";
import { membersApi, commonsApi, circlesApi } from "@/lib/api";
import Link from "next/link";
import { Zap, MessageSquare } from "lucide-react";

interface DormainTag { id: string; name: string }
interface Author { id: string; handle: string; display_name: string }

interface FeedThread {
  thread_id: string;
  title: string;
  body_preview: string;
  author: Author | null;
  dormain_tags: DormainTag[];
  state: string;
  post_count: number;
  created_at: string;
  sponsored_at: string | null;
  feed_relevance: number;
  relevance_source: string;
}

interface RawThread {
  id: string;
  title: string;
  body_preview?: string;
  body?: string;
  author: Author | null;
  tags?: DormainTag[];
  dormain_tags?: DormainTag[];
  state: string;
  post_count: number;
  created_at: string;
  sponsored_at: string | null;
}

interface Paginated<T> { items: T[]; total: number; page: number; page_size: number; has_next: boolean }

const STATE_BADGE: Record<string, string> = {
  open:      "bg-emerald-900/40 text-emerald-400 border-emerald-800/40",
  sponsored: "bg-[var(--gold-glow)] text-[var(--gold)] border-[var(--gold)]/30",
  frozen:    "bg-red-900/30 text-red-400 border-red-800/30",
  dissolved: "bg-zinc-800 text-zinc-500 border-zinc-700",
};

const RELEVANCE_LABEL: Record<string, string> = {
  mandate:  "mandate",
  curiosity: "curiosity",
  combined: "ranked",
  none:     "",
  chrono:   "",
};

function rel(iso: string) {
  const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (m < 60) return `${m}m ago`;
  if (m < 1440) return `${Math.floor(m / 60)}h ago`;
  return `${Math.floor(m / 1440)}d ago`;
}

function RelevancePip({ score, source }: { score: number; source: string }) {
  if (score <= 0 || source === "chrono" || source === "none") return null;
  const label = RELEVANCE_LABEL[source] ?? source;
  const fill = Math.round(score * 100);
  return (
    <span className="inline-flex items-center gap-1 text-[9px] font-mono text-[var(--gold)]">
      <span className="relative w-10 h-1 bg-[var(--border)] rounded-full overflow-hidden inline-block">
        <span className="absolute left-0 top-0 h-full bg-[var(--gold)] rounded-full"
          style={{ width: `${fill}%` }} />
      </span>
      {label && <span className="text-[var(--gold)]/60">{label}</span>}
    </span>
  );
}

function ThreadCard({ thread }: { thread: FeedThread }) {
  const tags = thread.dormain_tags ?? [];
  return (
    <Link href={`/org/commons/${thread.thread_id}`} className="block group">
      <article className="card p-5 hover:border-[var(--gold)]/40 transition-colors">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-medium text-[var(--text)]
              group-hover:text-[var(--gold)] transition-colors line-clamp-2 mb-1">
              {thread.title}
            </h2>
            <p className="text-xs text-[var(--text-muted)] line-clamp-2 mb-3 leading-relaxed">
              {thread.body_preview}
            </p>
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {tags.slice(0, 4).map(t => (
                  <span key={t.id}
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded-sm
                      bg-[var(--surface)] border border-[var(--border)] text-[var(--text-muted)]">
                    {t.name || t.id.slice(0, 8)}
                  </span>
                ))}
                {tags.length > 4 && (
                  <span className="text-[10px] font-mono text-[var(--text-dim)]">
                    +{tags.length - 4}
                  </span>
                )}
              </div>
            )}
            <div className="flex items-center gap-3 text-[10px] font-mono text-[var(--text-muted)]">
              <span>{thread.author?.handle ?? "—"}</span>
              <span>·</span>
              <span>{rel(thread.created_at)}</span>
              <span>·</span>
              <span className="flex items-center gap-1">
                <MessageSquare size={9} />
                {thread.post_count}
              </span>
              {thread.sponsored_at && (
                <>
                  <span>·</span>
                  <span className="text-[var(--gold)]">sponsored</span>
                </>
              )}
              <RelevancePip score={thread.feed_relevance} source={thread.relevance_source} />
            </div>
          </div>
          <span className={`shrink-0 text-[10px] font-mono px-1.5 py-0.5
            rounded border ${STATE_BADGE[thread.state] ?? "bg-zinc-800 text-zinc-400 border-zinc-700"}`}>
            {thread.state}
          </span>
        </div>
      </article>
    </Link>
  );
}

function ThreadSkeleton() {
  return (
    <div className="card p-5 animate-pulse">
      <div className="h-4 bg-[var(--surface-raised)] rounded w-3/4 mb-2" />
      <div className="h-3 bg-[var(--surface-raised)] rounded w-full mb-1" />
      <div className="h-3 bg-[var(--surface-raised)] rounded w-2/3 mb-4" />
      <div className="flex gap-2">
        <div className="h-5 bg-[var(--surface-raised)] rounded w-16" />
        <div className="h-5 bg-[var(--surface-raised)] rounded w-20" />
      </div>
    </div>
  );
}

export default function CommonsPage() {
  // Use the /members/me/feed endpoint for relevance-ranked results
  // with /commons/threads as the unranked fallback when search/filter active
  const [threads, setThreads] = useState<FeedThread[]>([]);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [page, setPage]       = useState(1);
  const [search, setSearch]   = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newBody, setNewBody]   = useState("");
  const [posting, setPosting]   = useState(false);
  const [useFeed, setUseFeed]   = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (useFeed && !search && !stateFilter) {
        // Relevance-ranked feed
        const res = await membersApi.feed({ page, page_size: 25 } as Parameters<typeof membersApi.feed>[0]);
        const d = res.data as Paginated<FeedThread>;
        setThreads(d.items ?? []);
        setTotal(d.total ?? 0);
      } else {
        // Search / filter mode — use commons threads endpoint
        const params: Record<string, unknown> = { page, page_size: 25 };
        if (search) params.search = search;
        if (stateFilter) params.state = stateFilter;
        const res = await commonsApi.threads(params);
        const d = res.data as Paginated<RawThread>;
        const items = (d.items ?? []).map(t => ({
          thread_id: t.id,
          title: t.title,
          body_preview: t.body_preview ?? (t.body?.slice(0, 280) ?? ""),
          author: t.author,
          dormain_tags: t.dormain_tags ?? t.tags ?? [],
          state: t.state,
          post_count: t.post_count,
          created_at: t.created_at,
          sponsored_at: t.sponsored_at,
          feed_relevance: 0,
          relevance_source: "chrono",
        } as FeedThread));
        setThreads(items);
        setTotal(d.total ?? 0);
      }
    } catch (ex: unknown) {
      setError(
        (ex as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          ?? "Failed to load Commons"
      );
    } finally { setLoading(false); }
  }, [page, search, stateFilter, useFeed]);

  useEffect(() => { load(); }, [load]);

  async function handleCreateThread(e: FormEvent) {
    e.preventDefault();
    if (!newTitle.trim() || !newBody.trim()) return;
    setPosting(true);
    try {
      await commonsApi.createThread({ title: newTitle.trim(), body: newBody.trim(), dormain_ids: [] });
      setCreating(false);
      setNewTitle(""); setNewBody("");
      load();
    } catch (ex: unknown) {
      alert(
        (ex as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          ?? "Failed to create thread"
      );
    } finally { setPosting(false); }
  }

  const hasFilter = !!(search || stateFilter);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-lg text-[var(--text)]">Commons</h1>
          <p className="text-xs text-[var(--text-muted)] font-mono mt-0.5">
            {useFeed && !hasFilter ? "Relevance-ranked feed" : "Browsing all threads"}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => { setUseFeed(!useFeed); setPage(1); }}
            className={`text-[10px] font-mono px-2 py-1 rounded border transition-colors ${
              useFeed && !hasFilter
                ? "border-[var(--gold)]/40 text-[var(--gold)] bg-[var(--gold-glow)]"
                : "border-[var(--border)] text-[var(--text-muted)] hover:border-[var(--border)]"
            }`}>
            <Zap size={9} className="inline mr-1" />
            Ranked
          </button>
          <button onClick={() => setCreating(!creating)}
            className="text-xs font-mono px-3 py-1.5 rounded border
              border-[var(--gold)]/40 text-[var(--gold)]
              hover:bg-[var(--gold-glow)] transition-colors">
            {creating ? "Cancel" : "+ New thread"}
          </button>
        </div>
      </div>

      {/* Create form */}
      {creating && (
        <form onSubmit={handleCreateThread} className="card p-5 space-y-3">
          <p className="section-label">New Commons thread</p>
          <input type="text" value={newTitle} onChange={e => setNewTitle(e.target.value)}
            placeholder="Thread title" required
            className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
              px-3 py-2 text-sm text-[var(--text)] font-mono
              placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--gold)]" />
          <textarea value={newBody} onChange={e => setNewBody(e.target.value)}
            placeholder="Opening argument or context…" required rows={5}
            className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
              px-3 py-2 text-sm text-[var(--text)] font-body resize-none
              placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--gold)]" />
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setCreating(false)}
              className="btn btn-ghost text-xs">Cancel</button>
            <button type="submit" disabled={posting}
              className="btn btn-primary text-xs disabled:opacity-40">
              {posting ? "Posting…" : "Post thread"}
            </button>
          </div>
        </form>
      )}

      {/* Filters */}
      <div className="flex gap-2">
        <input type="text" value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search threads…"
          className="flex-1 bg-[var(--surface)] border border-[var(--border)] rounded
            px-3 py-1.5 text-sm text-[var(--text)] font-mono
            placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--gold)]" />
        <select value={stateFilter} onChange={e => { setStateFilter(e.target.value); setPage(1); }}
          className="bg-[var(--surface)] border border-[var(--border)] rounded
            px-3 py-1.5 text-sm text-[var(--text)] font-mono
            focus:outline-none focus:border-[var(--gold)]">
          <option value="">All states</option>
          <option value="open">Open</option>
          <option value="sponsored">Sponsored</option>
          <option value="frozen">Frozen</option>
        </select>
      </div>

      {error && (
        <div className="text-xs font-mono text-red-400 bg-red-950/30
          border border-red-800/40 rounded px-4 py-3">
          {error}
        </div>
      )}

      <div className="space-y-3">
        {loading
          ? Array.from({ length: 5 }).map((_, i) => <ThreadSkeleton key={i} />)
          : threads.map(t => <ThreadCard key={t.thread_id} thread={t} />)
        }
        {!loading && threads.length === 0 && (
          <div className="text-center py-12 text-[var(--text-muted)] font-mono text-sm">
            No threads yet.{" "}
            <button onClick={() => setCreating(true)}
              className="text-[var(--gold)] hover:underline">
              Start one.
            </button>
          </div>
        )}
      </div>

      {total > 25 && (
        <div className="flex items-center justify-between text-xs font-mono text-[var(--text-muted)]">
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
