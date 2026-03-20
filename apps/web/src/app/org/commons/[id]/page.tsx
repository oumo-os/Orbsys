"use client";

import { useEffect, useState, useCallback, FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { commonsApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { ChevronLeft, MessageSquare, Star } from "lucide-react";

interface Author {
  id: string;
  handle: string;
  display_name: string;
}

interface Thread {
  id: string;
  title: string;
  body: string;
  author: Author;
  tags: { id: string; name: string }[];
  state: string;
  post_count: number;
  created_at: string;
  sponsored_at: string | null;
}

interface Post {
  id: string;
  body: string;
  author: Author;
  parent_post_id: string | null;
  created_at: string;
  edited_at: string | null;
  formal_reviews: {
    dormain_id: string;
    score_s: number;
    reviewed_at: string;
  }[];
}

function PostCard({
  post,
  onFormalReview,
}: {
  post: Post;
  onFormalReview: (postId: string) => void;
}) {
  const rel = (iso: string) => {
    const d = Date.now() - new Date(iso).getTime();
    const m = Math.floor(d / 60000);
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h`;
    return `${Math.floor(h / 24)}d`;
  };

  const avgScore =
    post.formal_reviews.length > 0
      ? post.formal_reviews.reduce((s, r) => s + r.score_s, 0) /
        post.formal_reviews.length
      : null;

  return (
    <div className="card p-5">
      {/* Author row */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-orbsys-surface-raised border border-orbsys-border flex items-center justify-center">
            <span className="text-[9px] font-mono text-orbsys-muted uppercase">
              {post.author.handle[0]}
            </span>
          </div>
          <span className="text-xs font-mono text-orbsys-text">
            {post.author.handle}
          </span>
          <span className="text-xs font-mono text-orbsys-muted">
            · {rel(post.created_at)}
          </span>
          {post.edited_at && (
            <span className="text-[10px] font-mono text-orbsys-muted">(edited)</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {avgScore !== null && (
            <span className="flex items-center gap-1 text-[10px] font-mono text-orbsys-gold">
              <Star size={10} />
              {avgScore.toFixed(2)}
            </span>
          )}
          <button
            onClick={() => onFormalReview(post.id)}
            className="text-[10px] font-mono text-orbsys-muted hover:text-orbsys-gold transition-colors px-2 py-0.5 border border-transparent hover:border-orbsys-gold/30 rounded"
          >
            Formal review
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="text-sm text-orbsys-text leading-relaxed whitespace-pre-wrap font-body">
        {post.body}
      </div>
    </div>
  );
}

interface FormalReviewModalProps {
  postId: string;
  onClose: () => void;
  onSuccess: () => void;
}

function FormalReviewModal({ postId, onClose, onSuccess }: FormalReviewModalProps) {
  const [dormainId, setDormainId] = useState("");
  const [score, setScore] = useState("0.5");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const s = parseFloat(score);
    if (isNaN(s) || s < 0 || s > 1) {
      setError("Score must be between 0.000 and 1.000");
      return;
    }
    if (!dormainId.trim()) {
      setError("Dormain ID required");
      return;
    }
    setSubmitting(true);
    try {
      await commonsApi.formalReview(postId, {
        dormain_id: dormainId.trim(),
        score_s: s,
      });
      onSuccess();
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Review submission failed"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="card p-6 w-full max-w-md">
        <h2 className="font-mono text-sm text-orbsys-text mb-4">
          File formal review
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-orbsys-muted mb-1 uppercase tracking-wider">
              Dormain ID
            </label>
            <input
              type="text"
              value={dormainId}
              onChange={(e) => setDormainId(e.target.value)}
              placeholder="uuid"
              required
              className="w-full bg-orbsys-surface border border-orbsys-border rounded px-3 py-2 text-sm font-mono text-orbsys-text focus:outline-none focus:border-orbsys-gold"
            />
            <p className="text-[10px] text-orbsys-muted font-mono mt-1">
              You must have w_s &gt; 0 in this dormain.
            </p>
          </div>
          <div>
            <label className="block text-xs font-mono text-orbsys-muted mb-1 uppercase tracking-wider">
              Score (0.000 – 1.000)
            </label>
            <input
              type="number"
              step="0.001"
              min="0"
              max="1"
              value={score}
              onChange={(e) => setScore(e.target.value)}
              required
              className="w-full bg-orbsys-surface border border-orbsys-border rounded px-3 py-2 text-sm font-mono text-orbsys-text focus:outline-none focus:border-orbsys-gold"
            />
          </div>
          {error && (
            <p className="text-xs font-mono text-red-400">{error}</p>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="text-xs font-mono text-orbsys-muted hover:text-orbsys-text px-3 py-1.5"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="text-xs font-mono px-4 py-1.5 rounded bg-orbsys-gold text-orbsys-void hover:brightness-110 disabled:opacity-50"
            >
              {submitting ? "Submitting…" : "Submit review"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function ThreadPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const member = useAuthStore((s) => s.member);

  const [thread, setThread] = useState<Thread | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newPost, setNewPost] = useState("");
  const [posting, setPosting] = useState(false);
  const [reviewPostId, setReviewPostId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [threadRes, postsRes] = await Promise.all([
        commonsApi.thread(id),
        commonsApi.posts(id),
      ]);
      setThread(threadRes.data);
      setPosts(postsRes.data?.items ?? postsRes.data ?? []);
    } catch {
      setError("Thread not found or you don't have access.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  async function handlePost(e: FormEvent) {
    e.preventDefault();
    if (!newPost.trim()) return;
    setPosting(true);
    try {
      await commonsApi.createPost(id, { body: newPost.trim() });
      setNewPost("");
      load();
    } catch (err: unknown) {
      alert(
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to post"
      );
    } finally {
      setPosting(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-4 bg-orbsys-surface rounded w-1/3 animate-pulse" />
        <div className="h-20 bg-orbsys-surface rounded animate-pulse" />
        <div className="h-16 bg-orbsys-surface rounded animate-pulse" />
      </div>
    );
  }

  if (error || !thread) {
    return (
      <div className="text-center py-16">
        <p className="text-sm font-mono text-orbsys-muted">{error ?? "Not found"}</p>
        <Link href="/org/commons" className="text-xs text-orbsys-gold hover:underline mt-2 block">
          ← Back to Commons
        </Link>
      </div>
    );
  }

  const isFrozen = thread.state === "frozen";

  return (
    <div className="space-y-6">
      {/* Back */}
      <Link
        href="/org/commons"
        className="inline-flex items-center gap-1.5 text-xs font-mono text-orbsys-muted hover:text-orbsys-text transition-colors"
      >
        <ChevronLeft size={12} />
        Commons
      </Link>

      {/* Thread header */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <h1 className="font-display text-xl text-orbsys-text leading-snug">
            {thread.title}
          </h1>
          <span
            className={`shrink-0 text-xs font-mono px-2 py-0.5 rounded border ${
              thread.state === "open"
                ? "border-emerald-800/40 text-emerald-400 bg-emerald-900/30"
                : thread.state === "sponsored"
                ? "border-orbsys-gold/30 text-orbsys-gold bg-orbsys-gold/10"
                : "border-zinc-700 text-zinc-500 bg-zinc-800"
            }`}
          >
            {thread.state}
          </span>
        </div>

        {/* Dormain tags */}
        {thread.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {thread.tags.map((tag) => (
              <span
                key={tag.id}
                className="text-xs font-mono px-2 py-0.5 rounded-sm bg-orbsys-surface border border-orbsys-border text-orbsys-muted"
              >
                {tag.name}
              </span>
            ))}
          </div>
        )}

        {/* Opening post body */}
        <div className="text-sm text-orbsys-text leading-relaxed whitespace-pre-wrap font-body mb-4">
          {thread.body}
        </div>

        {/* Author meta */}
        <div className="flex items-center gap-2 text-xs font-mono text-orbsys-muted">
          <div className="w-5 h-5 rounded-full bg-orbsys-surface-raised border border-orbsys-border flex items-center justify-center">
            <span className="text-[9px] uppercase">{thread.author.handle[0]}</span>
          </div>
          <span>{thread.author.handle}</span>
          <span>·</span>
          <span>
            {new Date(thread.created_at).toLocaleDateString("en-GB", {
              day: "numeric", month: "short", year: "numeric",
            })}
          </span>
          <span>·</span>
          <span className="flex items-center gap-1">
            <MessageSquare size={10} />
            {thread.post_count}
          </span>
          {thread.sponsored_at && (
            <>
              <span>·</span>
              <span className="text-orbsys-gold">Sponsored for Cell</span>
            </>
          )}
        </div>
      </div>

      {/* Posts */}
      {posts.length > 0 && (
        <div className="space-y-3">
          <p className="section-label">
            {posts.length} post{posts.length !== 1 ? "s" : ""}
          </p>
          {posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              onFormalReview={(pid) => setReviewPostId(pid)}
            />
          ))}
        </div>
      )}

      {/* New post */}
      {!isFrozen && (
        <div className="card p-5">
          <p className="section-label mb-3">Add to thread</p>
          <form onSubmit={handlePost} className="space-y-3">
            <textarea
              value={newPost}
              onChange={(e) => setNewPost(e.target.value)}
              placeholder="Your contribution…"
              rows={4}
              className="w-full bg-orbsys-surface border border-orbsys-border rounded px-3 py-2 text-sm text-orbsys-text font-body placeholder:text-orbsys-muted focus:outline-none focus:border-orbsys-gold resize-none"
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={posting || !newPost.trim()}
                className="text-xs font-mono px-4 py-1.5 rounded bg-orbsys-gold text-orbsys-void hover:brightness-110 disabled:opacity-50"
              >
                {posting ? "Posting…" : "Post reply"}
              </button>
            </div>
          </form>
        </div>
      )}

      {isFrozen && (
        <div className="card p-4 border-red-800/40 bg-red-950/20 text-center">
          <p className="text-xs font-mono text-red-400">
            This thread is frozen — no new posts.
          </p>
        </div>
      )}

      {/* Formal review modal */}
      {reviewPostId && (
        <FormalReviewModal
          postId={reviewPostId}
          onClose={() => setReviewPostId(null)}
          onSuccess={() => {
            setReviewPostId(null);
            load();
          }}
        />
      )}
    </div>
  );
}
