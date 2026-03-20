"use client";

import { useEffect, useState, useCallback } from "react";
import { commonsApi } from "@/lib/api";
import Link from "next/link";

interface DormainTag {
  id: string;
  name: string;
}

interface Author {
  id: string;
  handle: string;
  display_name: string;
}

interface Thread {
  id: string;
  title: string;
  body_preview: string;
  author: Author;
  tags: DormainTag[];
  state: string;
  post_count: number;
  created_at: string;
  sponsored_at: string | null;
}

interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

const STATE_BADGE: Record<string, string> = {
  open: "bg-emerald-900/40 text-emerald-400 border-emerald-800/40",
  sponsored: "bg-orbsys-gold/10 text-orbsys-gold border-orbsys-gold/30",
  frozen: "bg-red-900/30 text-red-400 border-red-800/30",
  dissolved: "bg-zinc-800 text-zinc-500 border-zinc-700",
};

function ThreadCard({ thread }: { thread: Thread }) {
  const badgeClass =
    STATE_BADGE[thread.state] ??
    "bg-zinc-800 text-zinc-400 border-zinc-700";

  const relativeTime = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  return (
    <Link href={`/commons/${thread.id}`} className="block group">
      <article className="card p-5 hover:border-orbsys-gold/40 transition-colors">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {/* Title */}
            <h2 className="text-sm font-medium text-orbsys-text group-hover:text-orbsys-gold transition-colors line-clamp-2 mb-1">
              {thread.title}
            </h2>

            {/* Preview */}
            <p className="text-xs text-orbsys-muted line-clamp-2 mb-3">
              {thread.body_preview}
            </p>

            {/* Dormain tags */}
            {thread.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {thread.tags.slice(0, 4).map((tag) => (
                  <span
                    key={tag.id}
                    className="text-xs font-mono px-2 py-0.5 rounded-sm bg-orbsys-surface border border-orbsys-border text-orbsys-muted"
                  >
                    {tag.name || tag.id.slice(0, 8)}
                  </span>
                ))}
                {thread.tags.length > 4 && (
                  <span className="text-xs font-mono text-orbsys-muted">
                    +{thread.tags.length - 4}
                  </span>
                )}
              </div>
            )}

            {/* Meta row */}
            <div className="flex items-center gap-3 text-xs font-mono text-orbsys-muted">
              <span>{thread.author.handle}</span>
              <span>·</span>
              <span>{relativeTime(thread.created_at)}</span>
              <span>·</span>
              <span>{thread.post_count} post{thread.post_count !== 1 ? "s" : ""}</span>
              {thread.sponsored_at && (
                <>
                  <span>·</span>
                  <span className="text-orbsys-gold">sponsored</span>
                </>
              )}
            </div>
          </div>

          {/* State badge */}
          <span
            className={`shrink-0 text-xs font-mono px-2 py-0.5 rounded border ${badgeClass}`}
          >
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
      <div className="h-4 bg-orbsys-surface rounded w-3/4 mb-2" />
      <div className="h-3 bg-orbsys-surface rounded w-full mb-1" />
      <div className="h-3 bg-orbsys-surface rounded w-2/3 mb-4" />
      <div className="flex gap-2">
        <div className="h-5 bg-orbsys-surface rounded w-16" />
        <div className="h-5 bg-orbsys-surface rounded w-20" />
      </div>
    </div>
  );
}

export default function CommonsPage() {
  const [data, setData] = useState<Paginated<Thread> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newBody, setNewBody] = useState("");
  const [posting, setPosting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, unknown> = { page, page_size: 25 };
      if (search) params.search = search;
      if (stateFilter) params.state = stateFilter;
      const res = await commonsApi.threads(params);
      setData(res.data);
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to load Commons"
      );
    } finally {
      setLoading(false);
    }
  }, [page, search, stateFilter]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreateThread(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim() || !newBody.trim()) return;
    setPosting(true);
    try {
      await commonsApi.createThread({
        title: newTitle.trim(),
        body: newBody.trim(),
        dormain_ids: [],
      });
      setCreating(false);
      setNewTitle("");
      setNewBody("");
      load();
    } catch (err: unknown) {
      alert(
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to create thread"
      );
    } finally {
      setPosting(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-lg text-orbsys-text">Commons</h1>
          <p className="text-xs text-orbsys-muted font-mono mt-0.5">
            Public deliberative surface
          </p>
        </div>
        <button
          onClick={() => setCreating(!creating)}
          className="text-xs font-mono px-3 py-1.5 rounded border border-orbsys-gold/40 text-orbsys-gold hover:bg-orbsys-gold/10 transition-colors"
        >
          {creating ? "Cancel" : "+ New thread"}
        </button>
      </div>

      {/* Create thread form */}
      {creating && (
        <form onSubmit={handleCreateThread} className="card p-5 space-y-3">
          <p className="section-label">New Commons thread</p>
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Thread title"
            required
            className="w-full bg-orbsys-surface border border-orbsys-border rounded px-3 py-2 text-sm text-orbsys-text font-mono placeholder:text-orbsys-muted focus:outline-none focus:border-orbsys-gold"
          />
          <textarea
            value={newBody}
            onChange={(e) => setNewBody(e.target.value)}
            placeholder="Opening argument or context…"
            required
            rows={5}
            className="w-full bg-orbsys-surface border border-orbsys-border rounded px-3 py-2 text-sm text-orbsys-text font-mono placeholder:text-orbsys-muted focus:outline-none focus:border-orbsys-gold resize-none"
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setCreating(false)}
              className="text-xs font-mono px-3 py-1.5 text-orbsys-muted hover:text-orbsys-text"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={posting}
              className="text-xs font-mono px-4 py-1.5 rounded bg-orbsys-gold text-orbsys-void hover:brightness-110 disabled:opacity-50"
            >
              {posting ? "Posting…" : "Post thread"}
            </button>
          </div>
        </form>
      )}

      {/* Filters */}
      <div className="flex gap-3 items-center">
        <input
          type="text"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search threads…"
          className="flex-1 bg-orbsys-surface border border-orbsys-border rounded px-3 py-1.5 text-sm text-orbsys-text font-mono placeholder:text-orbsys-muted focus:outline-none focus:border-orbsys-gold"
        />
        <select
          value={stateFilter}
          onChange={(e) => { setStateFilter(e.target.value); setPage(1); }}
          className="bg-orbsys-surface border border-orbsys-border rounded px-3 py-1.5 text-sm text-orbsys-text font-mono focus:outline-none focus:border-orbsys-gold"
        >
          <option value="">All states</option>
          <option value="open">Open</option>
          <option value="sponsored">Sponsored</option>
          <option value="frozen">Frozen</option>
        </select>
      </div>

      {/* Thread list */}
      {error && (
        <div className="text-xs font-mono text-red-400 bg-red-950/30 border border-red-800/40 rounded px-4 py-3">
          {error}
        </div>
      )}

      <div className="space-y-3">
        {loading
          ? Array.from({ length: 5 }).map((_, i) => <ThreadSkeleton key={i} />)
          : data?.items.map((thread) => (
              <ThreadCard key={thread.id} thread={thread} />
            ))}
        {!loading && data?.items.length === 0 && (
          <div className="text-center py-12 text-orbsys-muted font-mono text-sm">
            No threads yet.{" "}
            <button
              onClick={() => setCreating(true)}
              className="text-orbsys-gold hover:underline"
            >
              Start one.
            </button>
          </div>
        )}
      </div>

      {/* Pagination */}
      {data && data.total > data.page_size && (
        <div className="flex items-center justify-between text-xs font-mono text-orbsys-muted">
          <span>
            {(data.page - 1) * data.page_size + 1}–
            {Math.min(data.page * data.page_size, data.total)} of {data.total}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 rounded border border-orbsys-border hover:border-orbsys-gold/40 disabled:opacity-40 transition-colors"
            >
              ← Prev
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!data.has_next}
              className="px-3 py-1 rounded border border-orbsys-border hover:border-orbsys-gold/40 disabled:opacity-40 transition-colors"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
