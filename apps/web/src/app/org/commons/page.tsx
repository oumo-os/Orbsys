"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { commonsApi, cellsApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const T = {
  bg:"#050505", surface:"#080808", raised:"#0c0c0c",
  border:"#141414", dim:"#2a2a2a", muted:"#555555",
  text:"#cccccc", textSub:"#777777", textDim:"#3a3a3a",
  gold:"#c8a96e", goldDim:"#c8a96e22", green:"#5a8a6a",
  mono:"'DM Mono',monospace", serif:"'Lora',serif",
};

interface Thread {
  id:string; title:string; body?:string; state:string;
  author?:{handle:string}; created_at:string;
  dormain_tags?:{name:string;weight:number}[];
}

interface Cell {
  id:string; founding_mandate:string; state:string; created_at:string;
  initiating_member?:{handle:string};
}

function DomainPill({ name, weight }: { name:string; weight?:number }) {
  return (
    <span style={{
      display:"inline-flex", alignItems:"center", gap:3,
      padding:"1px 6px", borderRadius:10, marginRight:4, marginBottom:2,
      background:T.goldDim, border:`1px solid ${T.gold}30`,
      fontSize:8, fontFamily:T.mono, color:T.gold,
    }}>
      {name}{weight != null && <span style={{opacity:0.6}}>{Math.round(weight*100)}%</span>}
    </span>
  );
}

function TimeAgo({ iso }:{ iso:string }) {
  const d = (Date.now() - new Date(iso).getTime()) / 1000;
  const s = d<60 ? `${Math.floor(d)}s`
    : d<3600 ? `${Math.floor(d/60)}m`
    : d<86400 ? `${Math.floor(d/3600)}h`
    : `${Math.floor(d/86400)}d`;
  return <span style={{color:T.muted, fontSize:9}}>{s}</span>;
}

function ThreadRow({ thread, onClick }: { thread:Thread; onClick:()=>void }) {
  return (
    <div
      onClick={onClick}
      style={{
        padding:"11px 14px", borderBottom:`1px solid ${T.border}`,
        cursor:"pointer", transition:"background 0.1s",
      }}
      onMouseEnter={e=>(e.currentTarget.style.background=T.raised)}
      onMouseLeave={e=>(e.currentTarget.style.background="transparent")}
    >
      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
        <span style={{ fontSize:11, color:T.text, fontFamily:T.serif, lineHeight:1.4 }}>
          {thread.title}
        </span>
        <TimeAgo iso={thread.created_at} />
      </div>
      {thread.body && (
        <p style={{ margin:"0 0 5px", fontSize:10, color:T.textSub,
          fontFamily:T.serif, lineHeight:1.5,
          overflow:"hidden", display:"-webkit-box",
          WebkitLineClamp:2, WebkitBoxOrient:"vertical" }}>
          {thread.body}
        </p>
      )}
      <div style={{ display:"flex", alignItems:"center", flexWrap:"wrap" }}>
        {thread.dormain_tags?.map(t => (
          <DomainPill key={t.name} name={t.name} weight={t.weight} />
        ))}
        {thread.author && (
          <span style={{ fontSize:9, color:T.muted, marginLeft:"auto" }}>
            @{thread.author.handle}
          </span>
        )}
      </div>
    </div>
  );
}

function CellCard({ cell, onClick }: { cell:Cell; onClick:()=>void }) {
  const stateColor = cell.state==="active" ? T.green : T.muted;
  return (
    <div
      onClick={onClick}
      style={{
        padding:"9px 12px", borderBottom:`1px solid ${T.border}`,
        cursor:"pointer",
      }}
      onMouseEnter={e=>(e.currentTarget.style.background=T.raised)}
      onMouseLeave={e=>(e.currentTarget.style.background="transparent")}
    >
      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:3 }}>
        <span style={{ fontSize:10, color:T.text, fontFamily:T.serif, lineHeight:1.4,
          overflow:"hidden", display:"-webkit-box",
          WebkitLineClamp:2, WebkitBoxOrient:"vertical" }}>
          {cell.founding_mandate}
        </span>
      </div>
      <div style={{ display:"flex", justifyContent:"space-between", marginTop:4 }}>
        <span style={{ fontSize:8, color:stateColor, fontFamily:T.mono }}>{cell.state}</span>
        <TimeAgo iso={cell.created_at} />
      </div>
    </div>
  );
}

export default function CommonsPage() {
  const router = useRouter();
  const member = useAuthStore(s=>s.member);

  const [threads,     setThreads]     = useState<Thread[]>([]);
  const [cells,       setCells]       = useState<Cell[]>([]);
  const [newTitle,    setNewTitle]    = useState("");
  const [newBody,     setNewBody]     = useState("");
  const [composing,   setComposing]   = useState(false);
  const [loading,     setLoading]     = useState(true);
  const [posting,     setPosting]     = useState(false);
  const [tab,         setTab]         = useState<"ranked"|"new">("ranked");

  const load = useCallback(async () => {
    try {
      const [tr, cr] = await Promise.allSettled([
        commonsApi.threads({ page:1, page_size:40,
          sort: tab==="ranked" ? "relevance" : "created_at" }),
        cellsApi.list({ state:"active", page:1, page_size:12 }),
      ]);
      if (tr.status==="fulfilled")
        setThreads(tr.value.data?.items ?? tr.value.data ?? []);
      if (cr.status==="fulfilled")
        setCells(cr.value.data?.items ?? cr.value.data ?? []);
    } finally { setLoading(false); }
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  async function post() {
    if (!newTitle.trim()) return;
    setPosting(true);
    try {
      await commonsApi.create({ title:newTitle.trim(), body:newBody.trim() });
      setNewTitle(""); setNewBody(""); setComposing(false);
      load();
    } finally { setPosting(false); }
  }

  if (!member) return null;

  return (
    <div style={{ display:"flex", gap:1, height:"100%", overflow:"hidden" }}>

      {/* ── Main thread feed ────────────────────────────── */}
      <div style={{
        flex:1, display:"flex", flexDirection:"column",
        border:`1px solid ${T.border}`, borderRadius:6, overflow:"hidden",
        background:T.surface,
      }}>
        {/* Toolbar */}
        <div style={{
          display:"flex", alignItems:"center", justifyContent:"space-between",
          padding:"9px 14px", borderBottom:`1px solid ${T.border}`,
          flexShrink:0,
        }}>
          <div style={{ display:"flex", gap:0 }}>
            {(["ranked","new"] as const).map(t => (
              <button key={t} onClick={()=>setTab(t)} style={{
                padding:"4px 10px", background:"transparent",
                border:"none", cursor:"pointer", fontFamily:T.mono, fontSize:9,
                color: tab===t ? T.gold : T.muted,
                letterSpacing:1, textTransform:"uppercase",
                borderBottom: `1px solid ${tab===t ? T.gold : "transparent"}`,
              }}>{t==="ranked"?"Ranked":"New"}</button>
            ))}
          </div>
          <button
            onClick={()=>setComposing(c=>!c)}
            style={{
              padding:"4px 10px", background:composing?T.goldDim:"transparent",
              border:`1px solid ${composing?T.gold:T.dim}`,
              borderRadius:4, cursor:"pointer",
              fontFamily:T.mono, fontSize:9, color:composing?T.gold:T.muted,
              letterSpacing:1,
            }}
          >
            {composing ? "✕ cancel" : "+ new thread"}
          </button>
        </div>

        {/* Composer */}
        {composing && (
          <div style={{
            padding:"12px 14px", borderBottom:`1px solid ${T.border}`,
            background:T.raised, flexShrink:0,
          }}>
            <input
              autoFocus
              value={newTitle} onChange={e=>setNewTitle(e.target.value)}
              placeholder="Thread title…"
              style={{
                width:"100%", background:"transparent",
                border:"none", borderBottom:`1px solid ${T.border}`,
                color:T.text, fontFamily:T.serif, fontSize:13,
                padding:"4px 0 8px", marginBottom:8, outline:"none",
              }}
            />
            <textarea
              value={newBody} onChange={e=>setNewBody(e.target.value)}
              placeholder="Context, question, proposal… (optional)"
              rows={3}
              style={{
                width:"100%", background:"transparent",
                border:"none", borderBottom:`1px solid ${T.border}`,
                color:T.textSub, fontFamily:T.serif, fontSize:11,
                padding:"4px 0 8px", marginBottom:10, outline:"none",
                resize:"none", lineHeight:1.6,
              }}
            />
            <div style={{ display:"flex", justifyContent:"flex-end" }}>
              <button
                onClick={post} disabled={posting||!newTitle.trim()}
                style={{
                  padding:"5px 14px", background:T.goldDim,
                  border:`1px solid ${T.gold}50`, borderRadius:4,
                  color:T.gold, fontFamily:T.mono, fontSize:9,
                  cursor:"pointer", letterSpacing:1,
                  opacity: posting||!newTitle.trim() ? 0.4 : 1,
                }}
              >
                {posting ? "posting…" : "post thread →"}
              </button>
            </div>
          </div>
        )}

        {/* Thread list */}
        <div style={{ flex:1, overflowY:"auto" }}>
          {loading ? (
            <div style={{ padding:24, color:T.muted, fontSize:10, textAlign:"center" }}>
              Loading…
            </div>
          ) : threads.length===0 ? (
            <div style={{ padding:24, color:T.muted, fontSize:10, textAlign:"center" }}>
              No threads yet — start one above.
            </div>
          ) : threads.map(t => (
            <ThreadRow
              key={t.id} thread={t}
              onClick={()=>router.push(`/org/commons/${t.id}`)}
            />
          ))}
        </div>
      </div>

      {/* ── Right panel: active cells ────────────────────── */}
      <div style={{
        width:260, flexShrink:0,
        border:`1px solid ${T.border}`, borderRadius:6, overflow:"hidden",
        background:T.surface, display:"flex", flexDirection:"column",
      }}>
        <div style={{
          padding:"9px 12px", borderBottom:`1px solid ${T.border}`,
          display:"flex", justifyContent:"space-between", alignItems:"center",
          flexShrink:0,
        }}>
          <span style={{ fontSize:9, color:T.muted, letterSpacing:2,
            textTransform:"uppercase" }}>Active Cells</span>
          <button
            onClick={()=>router.push("/org/cells")}
            style={{ background:"none", border:"none", cursor:"pointer",
              fontSize:9, color:T.textSub, fontFamily:T.mono }}>
            all →
          </button>
        </div>

        <div style={{ flex:1, overflowY:"auto" }}>
          {cells.length===0 ? (
            <div style={{ padding:16, color:T.muted, fontSize:10 }}>
              No active cells.
            </div>
          ) : cells.map(c => (
            <CellCard
              key={c.id} cell={c}
              onClick={()=>router.push(`/org/cells/${c.id}`)}
            />
          ))}
        </div>

        {/* Quick cell creation — Circle member only */}
        <div style={{
          padding:"8px 12px", borderTop:`1px solid ${T.border}`,
          flexShrink:0,
        }}>
          <button
            onClick={()=>router.push("/org/cells?create=1")}
            style={{
              width:"100%", padding:"6px",
              background:"transparent",
              border:`1px solid ${T.dim}`,
              borderRadius:4, cursor:"pointer",
              fontFamily:T.mono, fontSize:9, color:T.muted,
              letterSpacing:1,
            }}
            onMouseEnter={e=>(e.currentTarget.style.borderColor=T.gold)}
            onMouseLeave={e=>(e.currentTarget.style.borderColor=T.dim)}
          >
            + open a cell
          </button>
        </div>
      </div>
    </div>
  );
}
