"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { commonsApi, cellsApi } from "@/lib/api";
import { T, SectionHead, DomainTag, Dot } from "@/components/ui";

interface Thread {
  id: string;
  title: string;
  body: string;
  author_handle?: string;
  author_name?: string;
  state: string;
  created_at: string;
  post_count?: number;
  dormain_tags?: { dormain: string; weight: number }[];
}

function PostCard({ thread }: { thread: Thread }) {
  const router = useRouter();
  const tags = thread.dormain_tags || [];

  return (
    <div
      style={{
        padding:"16px", borderRadius:8,
        border:`1px solid ${T.border}`, background:T.surface, marginBottom:8,
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = T.border2}
      onMouseLeave={e => e.currentTarget.style.borderColor = T.border}
    >
      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:10 }}>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <div style={{
            width:26, height:26, borderRadius:"50%",
            background:`${T.blue}22`, border:`1px solid ${T.blue}30`,
            display:"flex", alignItems:"center", justifyContent:"center",
            fontSize:11, color:T.blue, flexShrink:0,
          }}>{(thread.author_name || thread.author_handle || "?")[0]}</div>
          <span style={{ fontSize:12, color:T.text, fontFamily:T.serif }}>
            {thread.author_name || thread.author_handle || "Unknown"}
          </span>
        </div>
        <span style={{ fontSize:9, color:T.muted, fontFamily:T.mono }}>
          {new Date(thread.created_at).toLocaleDateString()}
        </span>
      </div>
      <p style={{
        margin:"0 0 10px", fontSize:13, color:"#bbb",
        fontFamily:T.serif, lineHeight:1.65,
      }}>{thread.title}</p>
      {tags.length > 0 && (
        <div style={{ display:"flex", flexWrap:"wrap", gap:4, marginBottom:10 }}>
          {tags.map(t => <DomainTag key={t.dormain} d={t.dormain} w={t.weight}/>)}
        </div>
      )}
      <div style={{ display:"flex", gap:16 }}>
        <button style={{
          display:"flex", alignItems:"center", gap:4, border:"none",
          background:"transparent", color:T.muted, fontFamily:T.mono,
          fontSize:10, cursor:"pointer", padding:0,
        }}>↩ {thread.post_count || 0}</button>
        <button
          onClick={() => router.push(`/org/commons/${thread.id}`)}
          style={{
            marginLeft:"auto", border:`1px solid ${T.border2}`,
            borderRadius:4, background:"transparent", color:T.muted,
            fontFamily:T.mono, fontSize:9, cursor:"pointer",
            padding:"3px 10px", letterSpacing:0.5,
          }}
        >View →</button>
      </div>
    </div>
  );
}

export default function CommonsPage() {
  const router = useRouter();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(true);
  const [newPost, setNewPost] = useState("");
  const [posting, setPosting] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await commonsApi.threads();
      const data = res.data;
      setThreads(data?.items ?? data ?? []);
    } catch { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function createThread() {
    if (!newPost.trim()) return;
    setPosting(true);
    try {
      await commonsApi.create({ title: newPost.trim().slice(0, 200), body: newPost.trim() });
      setNewPost("");
      await load();
    } catch { /* silent */ }
    setPosting(false);
  }

  return (
    <div style={{ display:"flex", gap:20, flex:1 }}>
      {/* Main feed */}
      <div style={{ flex:1, minWidth:0 }}>
        <SectionHead label="Commons" sub="Open threads · signed to domains by Inferential Engine"/>
        <div style={{
          padding:"14px 16px", borderRadius:8,
          border:`1px solid ${T.border2}`, background:T.panel, marginBottom:20,
        }}>
          <textarea
            value={newPost}
            onChange={e => setNewPost(e.target.value)}
            placeholder="Post to the commons — the Inferential Engine will sign domain weights…"
            style={{
              width:"100%", background:"transparent", border:"none", outline:"none",
              color:"#888", fontFamily:T.serif, fontSize:12, resize:"none",
              lineHeight:1.7, boxSizing:"border-box",
            }}
            rows={2}
          />
          <div style={{ display:"flex", justifyContent:"flex-end", marginTop:6 }}>
            <button
              onClick={createThread}
              disabled={posting || !newPost.trim()}
              style={{
                padding:"6px 16px", border:`1px solid ${T.goldDim}`,
                borderRadius:5, background:"transparent", color:T.gold,
                fontFamily:T.mono, fontSize:10, cursor:"pointer", letterSpacing:1,
                opacity: posting || !newPost.trim() ? 0.4 : 1,
              }}
            >{posting ? "Posting…" : "Post"}</button>
          </div>
        </div>

        {loading ? (
          <p style={{ color:T.muted, fontSize:11, fontFamily:T.mono, padding:20, textAlign:"center" }}>Loading…</p>
        ) : threads.length === 0 ? (
          <p style={{ color:T.muted, fontSize:11, fontFamily:T.mono, padding:20, textAlign:"center" }}>No threads yet. Be the first to post.</p>
        ) : (
          threads.map(t => <PostCard key={t.id} thread={t}/>)
        )}
      </div>

      {/* Right rail */}
      <div style={{ width:236, flexShrink:0 }}>
        <SectionHead label="Your Stream"/>
        <div style={{ display:"flex", flexDirection:"column", gap:0 }}>
          {[
            ["No pending notifications", T.green],
          ].map(([text, color], i) => (
            <div key={i} style={{
              display:"flex", gap:8, alignItems:"flex-start",
              padding:"9px 0", borderBottom:`1px solid ${T.border}`,
            }}>
              <Dot color={color as string}/>
              <span style={{ fontSize:11, color:T.textSub, fontFamily:T.serif }}>{text as string}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
