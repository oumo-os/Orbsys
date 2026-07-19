"use client";

import { useEffect, useState, useCallback, FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { commonsApi, circlesApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { ChevronLeft, MessageSquare, Star, Zap, CheckCircle } from "lucide-react";

interface Author { id: string; handle: string; display_name: string }
interface CircleRef { id: string; name: string }

interface Thread {
  id: string; title: string; body: string; author: Author;
  tags: { id: string; name: string }[];
  state: string; post_count: number;
  created_at: string; sponsored_at: string | null;
  sponsoring_cell_id: string | null;
}

interface Post {
  id: string; body: string; author: Author;
  parent_post_id: string | null;
  created_at: string; edited_at: string | null;
  formal_reviews: { dormain_id: string; score_s: number; reviewed_at: string }[];
}

interface SponsorDraft {
  draft_id: string; founding_mandate: string;
  key_themes: string[];
}

// ── Formal review modal ───────────────────────────────────────────────────────
function FormalReviewModal({ postId, onClose, onSuccess }: {
  postId: string; onClose: () => void; onSuccess: () => void;
}) {
  const [dormainId, setDormainId] = useState("");
  const [score, setScore] = useState("0.7");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true); setError(null);
    try {
      await commonsApi.formalReview(postId, { dormain_id: dormainId, score_s: parseFloat(score) });
      onSuccess();
    } catch (ex: unknown) {
      setError(
        (ex as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          ?? "Review failed"
      );
    } finally { setSubmitting(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
      <div className="card p-6 w-full max-w-sm">
        <h2 className="font-display text-base text-[var(--text)] mb-4">File formal review</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="section-label block mb-1.5">Dormain ID</label>
            <input type="text" value={dormainId} onChange={e => setDormainId(e.target.value)}
              placeholder="uuid" required
              className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                px-3 py-2 text-sm font-mono text-[var(--text)]
                focus:outline-none focus:border-[var(--gold)]" />
            <p className="text-[10px] text-[var(--text-dim)] font-mono mt-1">
              You must have W_s &gt; 0 in this dormain.
            </p>
          </div>
          <div>
            <label className="section-label block mb-1.5">Score (0.000 – 1.000)</label>
            <input type="number" step="0.001" min="0" max="1"
              value={score} onChange={e => setScore(e.target.value)} required
              className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                px-3 py-2 text-sm font-mono text-[var(--text)]
                focus:outline-none focus:border-[var(--gold)]" />
          </div>
          {error && <p className="text-xs font-mono text-red-400">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="btn btn-ghost text-xs">
              Cancel
            </button>
            <button type="submit" disabled={submitting} className="btn btn-primary text-xs disabled:opacity-40">
              {submitting ? "Submitting…" : "Submit review"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Sponsor modal — Step 1: get draft ────────────────────────────────────────
function SponsorDraftModal({ threadId, onConfirm, onClose }: {
  threadId: string;
  onConfirm: (draft: SponsorDraft, circleIds: string[]) => void;
  onClose: () => void;
}) {
  const [draft, setDraft]           = useState<SponsorDraft | null>(null);
  const [circles, setCircles]       = useState<CircleRef[]>([]);
  const [invited, setInvited]       = useState<string[]>([]);
  const [mandate, setMandate]       = useState("");
  const [loading, setLoading]       = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [err, setErr]               = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      commonsApi.sponsorDraft(threadId),
      circlesApi.list(),
    ]).then(([draftRes, circlesRes]) => {
      const d = draftRes.data as SponsorDraft;
      setDraft(d);
      setMandate(d.founding_mandate);
      setCircles((circlesRes.data as CircleRef[] | { items?: CircleRef[] })
        instanceof Array
        ? circlesRes.data as CircleRef[]
        : ((circlesRes.data as { items?: CircleRef[] }).items ?? [])
      );
    }).catch(ex => {
      setErr(
        (ex as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? "Failed to generate draft"
      );
    }).finally(() => setLoading(false));
  }, [threadId]);

  async function confirm(e: FormEvent) {
    e.preventDefault();
    if (!draft || invited.length === 0) return;
    setConfirming(true); setErr(null);
    try {
      await commonsApi.confirmSponsor(threadId, {
        founding_mandate: mandate,
        invited_circle_ids: invited,
        draft_id: draft.draft_id,
      });
      onConfirm({ ...draft, founding_mandate: mandate }, invited);
    } catch (ex: unknown) {
      setErr(
        (ex as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? "Sponsorship failed"
      );
    } finally { setConfirming(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="card w-full max-w-lg my-auto">
        <div className="p-5 border-b border-[var(--border)] flex items-center justify-between">
          <div>
            <h2 className="font-display text-base text-[var(--text)]">Sponsor as Cell</h2>
            <p className="text-xs font-mono text-[var(--text-muted)] mt-0.5">
              Insight Engine draft — edit before confirming
            </p>
          </div>
          <button onClick={onClose}
            className="text-[var(--text-muted)] hover:text-[var(--text)] text-xl leading-none">
            ×
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <div className="w-6 h-6 border border-[var(--gold)]/40 border-t-[var(--gold)]
              rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs font-mono text-[var(--text-muted)]">
              Generating mandate draft…
            </p>
          </div>
        ) : err ? (
          <div className="p-6">
            <p className="text-sm font-mono text-red-400 mb-3">{err}</p>
            <button onClick={onClose} className="btn btn-ghost text-xs">Close</button>
          </div>
        ) : (
          <form onSubmit={confirm} className="p-5 space-y-5">
            {/* Key themes from Insight Engine */}
            {draft?.key_themes && draft.key_themes.length > 0 && (
              <div className="p-3 rounded bg-[var(--gold-glow)] border border-[var(--gold)]/20">
                <p className="text-[9px] font-mono uppercase tracking-wider
                  text-[var(--gold)] mb-2">Key themes identified</p>
                <ul className="space-y-1">
                  {draft.key_themes.slice(0, 3).map((t, i) => (
                    <li key={i} className="text-xs text-[var(--text)] flex gap-2">
                      <span className="text-[var(--gold)] shrink-0">·</span>{t}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Founding mandate */}
            <div>
              <label className="section-label block mb-2">Founding mandate</label>
              <textarea value={mandate} onChange={e => setMandate(e.target.value)}
                rows={6} required
                className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                  px-3 py-2 text-sm font-body text-[var(--text)] resize-none
                  focus:outline-none focus:border-[var(--gold)]" />
            </div>

            {/* Invite circles */}
            <div>
              <label className="section-label block mb-2">
                Invite circles <span className="text-red-400">*</span>
                <span className="normal-case text-[var(--text-dim)] ml-1">
                  (determines who deliberates)
                </span>
              </label>
              {circles.length === 0 ? (
                <p className="text-xs font-mono text-[var(--text-muted)]">
                  No circles available — you must be a circle member to sponsor.
                </p>
              ) : (
                <div className="space-y-1.5 max-h-36 overflow-y-auto">
                  {circles.map(c => (
                    <label key={c.id} className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" className="accent-[var(--gold)]"
                        checked={invited.includes(c.id)}
                        onChange={e => setInvited(prev =>
                          e.target.checked ? [...prev, c.id] : prev.filter(x => x !== c.id)
                        )} />
                      <span className="text-xs font-mono text-[var(--text)]">{c.name}</span>
                    </label>
                  ))}
                </div>
              )}
              {invited.length === 0 && circles.length > 0 && (
                <p className="text-[10px] font-mono text-amber-400 mt-1">
                  Select at least one circle
                </p>
              )}
            </div>

            {err && (
              <div className="text-xs font-mono text-red-400 bg-[var(--red-dim)]
                border border-red-800/40 rounded px-3 py-2">{err}</div>
            )}

            <div className="flex gap-3 pt-1">
              <button type="button" onClick={onClose} className="btn btn-ghost flex-1 text-xs">
                Cancel
              </button>
              <button type="submit"
                disabled={confirming || invited.length === 0}
                className="btn btn-primary flex-1 text-xs gap-1.5 disabled:opacity-40">
                <Zap size={11} />
                {confirming ? "Creating cell…" : "Create deliberation cell"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// ── Post card ─────────────────────────────────────────────────────────────────
function PostCard({ post, onFormalReview }: {
  post: Post; onFormalReview: (postId: string) => void;
}) {
  const r = (iso: string) => {
    const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
    if (m < 60) return `${m}m`;
    if (m < 1440) return `${Math.floor(m / 60)}h`;
    return `${Math.floor(m / 1440)}d`;
  };
  const avgScore = post.formal_reviews.length > 0
    ? post.formal_reviews.reduce((s, rev) => s + rev.score_s, 0) / post.formal_reviews.length
    : null;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-[var(--surface-raised)]
            border border-[var(--border)] flex items-center justify-center">
            <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase">
              {post.author.handle[0]}
            </span>
          </div>
          <span className="text-xs font-mono text-[var(--text)]">{post.author.handle}</span>
          <span className="text-[10px] font-mono text-[var(--text-dim)]">· {r(post.created_at)}</span>
          {post.edited_at && (
            <span className="text-[9px] font-mono text-[var(--text-dim)]">(edited)</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {avgScore !== null && (
            <span className="flex items-center gap-1 text-[10px] font-mono text-[var(--gold)]">
              <Star size={9} />
              {avgScore.toFixed(2)}
            </span>
          )}
          <button onClick={() => onFormalReview(post.id)}
            className="text-[10px] font-mono text-[var(--text-dim)]
              hover:text-[var(--gold)] transition-colors">
            Review
          </button>
        </div>
      </div>
      <p className="text-sm text-[var(--text)] leading-relaxed whitespace-pre-wrap font-body">
        {post.body}
      </p>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ThreadPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const member = useAuthStore(s => s.member);

  const [thread, setThread]           = useState<Thread | null>(null);
  const [posts, setPosts]             = useState<Post[]>([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState<string | null>(null);
  const [newPost, setNewPost]         = useState("");
  const [posting, setPosting]         = useState(false);
  const [reviewPostId, setReviewPostId] = useState<string | null>(null);
  const [showSponsor, setShowSponsor] = useState(false);
  const [sponsored, setSponsored]     = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [threadRes, postsRes] = await Promise.all([
        commonsApi.thread(id),
        commonsApi.posts(id),
      ]);
      setThread(threadRes.data as Thread);
      const postsData = postsRes.data;
      setPosts(
        Array.isArray(postsData) ? postsData :
        (postsData as { items?: Post[] })?.items ?? []
      );
    } catch {
      setError("Thread not found or you don't have access.");
    } finally { setLoading(false); }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  async function handlePost(e: FormEvent) {
    e.preventDefault();
    if (!newPost.trim()) return;
    setPosting(true);
    try {
      await commonsApi.createPost(id, { body: newPost.trim() });
      setNewPost(""); load();
    } catch (ex: unknown) {
      alert(
        (ex as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? "Failed"
      );
    } finally { setPosting(false); }
  }

  function handleSponsored(_draft: SponsorDraft, _circles: string[]) {
    setShowSponsor(false);
    setSponsored(true);
    load();
  }

  if (loading) return (
    <div className="space-y-4">
      {[1, 2, 3].map(i => (
        <div key={i} className="card p-5 animate-pulse">
          <div className="h-4 bg-[var(--surface-raised)] rounded w-3/4 mb-3" />
          <div className="h-3 bg-[var(--surface-raised)] rounded w-full" />
        </div>
      ))}
    </div>
  );

  if (error || !thread) return (
    <div className="text-center py-16">
      <p className="text-sm font-mono text-[var(--text-muted)] mb-2">
        {error ?? "Thread not found"}
      </p>
      <Link href="/org/commons"
        className="text-xs text-[var(--gold)] hover:underline">
        ← Commons
      </Link>
    </div>
  );

  const isOpen   = thread.state === "open";
  const isFrozen = thread.state === "frozen";
  const isSponsored = thread.state === "sponsored" || sponsored;
  const isMine = thread.author.id === member?.id;

  return (
    <div className="space-y-5">
      <Link href="/org/commons"
        className="inline-flex items-center gap-1.5 text-xs font-mono
          text-[var(--text-muted)] hover:text-[var(--text)] transition-colors">
        <ChevronLeft size={12} /> Commons
      </Link>

      {/* Thread header */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <h1 className="font-display text-xl text-[var(--text)] leading-snug flex-1">
            {thread.title}
          </h1>
          <div className="flex items-center gap-2 shrink-0">
            {isOpen && (
              <button onClick={() => setShowSponsor(true)}
                className="btn text-xs gap-1.5 bg-[var(--gold-glow)]
                  border border-[var(--gold)]/40 text-[var(--gold)]
                  hover:bg-[var(--gold)]/20 transition-colors">
                <Zap size={11} />
                Sponsor
              </button>
            )}
            <span className={`text-xs font-mono px-2 py-0.5 rounded border ${
              isOpen      ? "border-emerald-800/40 text-emerald-400 bg-emerald-900/30" :
              isSponsored ? "border-[var(--gold)]/30 text-[var(--gold)] bg-[var(--gold-glow)]" :
                            "border-zinc-700 text-zinc-500 bg-zinc-800"
            }`}>
              {thread.state}
            </span>
          </div>
        </div>

        {thread.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {thread.tags.map(tag => (
              <span key={tag.id}
                className="text-[10px] font-mono px-2 py-0.5 rounded-sm
                  bg-[var(--surface)] border border-[var(--border)] text-[var(--text-muted)]">
                {tag.name}
              </span>
            ))}
          </div>
        )}

        <p className="text-sm text-[var(--text)] leading-relaxed whitespace-pre-wrap font-body mb-4">
          {thread.body}
        </p>

        <div className="flex items-center gap-3 text-[10px] font-mono text-[var(--text-muted)]">
          <div className="w-5 h-5 rounded-full bg-[var(--surface-raised)]
            border border-[var(--border)] flex items-center justify-center">
            <span className="text-[8px] uppercase">{thread.author.handle[0]}</span>
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
            <MessageSquare size={9} /> {thread.post_count}
          </span>
          {isSponsored && thread.sponsoring_cell_id && (
            <>
              <span>·</span>
              <Link href={`/org/cells/${thread.sponsoring_cell_id}`}
                className="text-[var(--gold)] flex items-center gap-1 hover:underline">
                <CheckCircle size={9} /> Cell →
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Sponsored banner */}
      {(sponsored || isSponsored) && thread.sponsoring_cell_id && (
        <div className="card p-4 border-[var(--gold)]/30 bg-[var(--gold-glow)]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-[var(--gold)] flex items-center gap-2">
              <CheckCircle size={12} /> Thread sponsored — deliberation cell active
            </span>
            <Link href={`/org/cells/${thread.sponsoring_cell_id}`}
              className="text-[10px] font-mono text-[var(--gold)] hover:underline">
              Go to cell →
            </Link>
          </div>
        </div>
      )}

      {/* Posts */}
      {posts.length > 0 && (
        <div className="space-y-3">
          <p className="section-label">
            {posts.length} post{posts.length !== 1 ? "s" : ""}
          </p>
          {posts.map(p => (
            <PostCard key={p.id} post={p}
              onFormalReview={pid => setReviewPostId(pid)} />
          ))}
        </div>
      )}

      {/* New post */}
      {!isFrozen && (
        <div className="card p-5">
          <p className="section-label mb-3">Add to thread</p>
          <form onSubmit={handlePost} className="space-y-3">
            <textarea value={newPost} onChange={e => setNewPost(e.target.value)}
              placeholder="Your contribution…" rows={4}
              className="w-full bg-[var(--surface)] border border-[var(--border)] rounded
                px-3 py-2 text-sm font-body text-[var(--text)] resize-none
                placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--gold)]" />
            <div className="flex justify-end">
              <button type="submit" disabled={posting || !newPost.trim()}
                className="btn btn-primary text-xs disabled:opacity-40">
                {posting ? "Posting…" : "Post reply"}
              </button>
            </div>
          </form>
        </div>
      )}

      {isFrozen && (
        <div className="card p-4 border-red-800/40 bg-red-950/20 text-center">
          <p className="text-xs font-mono text-red-400">Thread frozen — no new posts.</p>
        </div>
      )}

      {reviewPostId && (
        <FormalReviewModal
          postId={reviewPostId}
          onClose={() => setReviewPostId(null)}
          onSuccess={() => { setReviewPostId(null); load(); }}
        />
      )}

      {showSponsor && (
        <SponsorDraftModal
          threadId={id}
          onConfirm={handleSponsored}
          onClose={() => setShowSponsor(false)}
        />
      )}
    </div>
  );
}
