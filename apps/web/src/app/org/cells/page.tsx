"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { cellsApi, circlesApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const T = {
  bg:"#050505", surface:"#080808", raised:"#0c0c0c",
  border:"#141414", dim:"#2a2a2a", muted:"#555555",
  text:"#cccccc", textSub:"#777777", textDim:"#3a3a3a",
  gold:"#c8a96e", goldDim:"#c8a96e22",
  green:"#5a8a6a", red:"#c87a6e",
  mono:"'DM Mono',monospace", serif:"'Lora',serif",
};

const STATE_COLOR: Record<string,string> = {
  active: T.green, voted: T.gold,
  crystallised: T.gold, dissolved: T.muted, closed: T.muted,
};

interface Cell {
  id:string; founding_mandate:string; state:string; access:string;
  cell_type:string; created_at:string;
  initiating_member?:{handle:string};
  commons_thread_id?:string|null;
}

interface Circle { id:string; name:string; }

export default function CellsPage() {
  const router      = useRouter();
  const params      = useSearchParams();
  const member      = useAuthStore(s=>s.member);

  const [cells,    setCells]    = useState<Cell[]>([]);
  const [circles,  setCircles]  = useState<Circle[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [creating, setCreating] = useState(params.get("create")==="1");
  const [mandate,  setMandate]  = useState("");
  const [circleId, setCircleId] = useState("");
  const [access,   setAccess]   = useState<"closed"|"open">("closed");
  const [posting,  setPosting]  = useState(false);
  const [filter,   setFilter]   = useState<"active"|"all">("active");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [cRes, rRes] = await Promise.allSettled([
        cellsApi.list({ state: filter==="active"?"active":undefined, page:1, page_size:50 }),
        circlesApi.list(),
      ]);
      if (cRes.status==="fulfilled") setCells(cRes.value.data?.items ?? []);
      if (rRes.status==="fulfilled") setCircles(rRes.value.data?.items ?? rRes.value.data ?? []);
    } finally { setLoading(false); }
  }, [filter]);

  useEffect(()=>{ load(); }, [load]);

  async function createCell() {
    if (!mandate.trim()) return;
    setPosting(true);
    try {
      const res = await cellsApi.create({
        mandate: mandate.trim(),
        circle_id: circleId || null,
        access,
      });
      setCreating(false); setMandate(""); setCircleId(""); load();
      router.push(`/org/cells/${res.data.id}`);
    } finally { setPosting(false); }
  }

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%",
      border:`1px solid ${T.border}`, borderRadius:6, overflow:"hidden",
      background:T.surface }}>

      {/* Toolbar */}
      <div style={{
        display:"flex", alignItems:"center", justifyContent:"space-between",
        padding:"9px 14px", borderBottom:`1px solid ${T.border}`, flexShrink:0,
      }}>
        <div style={{ display:"flex", gap:0 }}>
          {(["active","all"] as const).map(f=>(
            <button key={f} onClick={()=>setFilter(f)} style={{
              padding:"4px 10px", background:"transparent", border:"none",
              cursor:"pointer", fontFamily:T.mono, fontSize:9,
              color:filter===f?T.gold:T.muted, letterSpacing:1, textTransform:"uppercase",
              borderBottom:`1px solid ${filter===f?T.gold:"transparent"}`,
            }}>{f}</button>
          ))}
        </div>
        <button onClick={()=>setCreating(c=>!c)} style={{
          padding:"4px 10px", background:creating?T.goldDim:"transparent",
          border:`1px solid ${creating?T.gold:T.dim}`, borderRadius:4,
          cursor:"pointer", fontFamily:T.mono, fontSize:9,
          color:creating?T.gold:T.muted, letterSpacing:1,
        }}>
          {creating?"✕ cancel":"+ open cell"}
        </button>
      </div>

      {/* Create form — internal cell, no Commons thread needed */}
      {creating && (
        <div style={{ padding:"14px", borderBottom:`1px solid ${T.border}`,
          background:T.raised, flexShrink:0 }}>
          <p style={{ margin:"0 0 10px", fontSize:9, color:T.muted,
            letterSpacing:2, textTransform:"uppercase" }}>
            Internal deliberation cell
          </p>
          <textarea
            autoFocus value={mandate}
            onChange={e=>setMandate(e.target.value)}
            placeholder="What is this cell for? Mandate / purpose…"
            rows={3}
            style={{ width:"100%", background:"transparent", border:"none",
              borderBottom:`1px solid ${T.border}`, color:T.text,
              fontFamily:T.serif, fontSize:12, padding:"4px 0 8px",
              marginBottom:10, outline:"none", resize:"none", lineHeight:1.6 }}
          />
          <div style={{ display:"flex", gap:8, marginBottom:10 }}>
            <select value={circleId} onChange={e=>setCircleId(e.target.value)}
              style={{ flex:1, background:T.raised, border:`1px solid ${T.border}`,
                color:circleId?T.text:T.muted, fontFamily:T.mono, fontSize:10,
                padding:"5px 8px", borderRadius:4, outline:"none" }}>
              <option value="">No circle assigned</option>
              {circles.map(c=>(
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <div style={{ display:"flex", gap:4 }}>
              {(["closed","open"] as const).map(a=>(
                <button key={a} onClick={()=>setAccess(a)} style={{
                  padding:"5px 10px", borderRadius:4, cursor:"pointer",
                  fontFamily:T.mono, fontSize:9, letterSpacing:1,
                  background: access===a?T.goldDim:"transparent",
                  border:`1px solid ${access===a?T.gold:T.dim}`,
                  color:access===a?T.gold:T.muted,
                }}>{a}</button>
              ))}
            </div>
          </div>
          <div style={{ display:"flex", justifyContent:"space-between",
            alignItems:"center" }}>
            <p style={{ margin:0, fontSize:9, color:T.muted }}>
              {access==="closed"?"Visible to invited circle only":"All members can read and post"}
            </p>
            <button onClick={createCell}
              disabled={posting||!mandate.trim()} style={{
                padding:"5px 14px", background:T.goldDim,
                border:`1px solid ${T.gold}50`, borderRadius:4,
                color:T.gold, fontFamily:T.mono, fontSize:9, cursor:"pointer",
                letterSpacing:1, opacity:posting||!mandate.trim()?0.4:1,
              }}>
              {posting?"opening…":"open cell →"}
            </button>
          </div>
        </div>
      )}

      {/* Cell list */}
      <div style={{ flex:1, overflowY:"auto" }}>
        {loading ? (
          <div style={{ padding:24, color:T.muted, fontSize:10, textAlign:"center" }}>
            Loading…
          </div>
        ) : cells.length===0 ? (
          <div style={{ padding:24, color:T.muted, fontSize:10, textAlign:"center" }}>
            No {filter==="active"?"active ":""}cells.
          </div>
        ) : cells.map((cell,i)=>(
          <div key={cell.id}
            onClick={()=>router.push(`/org/cells/${cell.id}`)}
            style={{
              padding:"11px 14px",
              borderBottom: i<cells.length-1?`1px solid ${T.border}`:"none",
              cursor:"pointer",
            }}
            onMouseEnter={e=>(e.currentTarget.style.background=T.raised)}
            onMouseLeave={e=>(e.currentTarget.style.background="transparent")}
          >
            <div style={{ display:"flex", justifyContent:"space-between",
              marginBottom:4 }}>
              <span style={{ fontSize:11, color:T.text, fontFamily:T.serif,
                lineHeight:1.4, flex:1, marginRight:8 }}>
                {cell.founding_mandate.slice(0,120)}
                {cell.founding_mandate.length>120?"…":""}
              </span>
              <span style={{ fontSize:9, color:STATE_COLOR[cell.state]??T.muted,
                fontFamily:T.mono, flexShrink:0 }}>
                {cell.state}
              </span>
            </div>
            <div style={{ display:"flex", gap:8, alignItems:"center" }}>
              <span style={{ fontSize:8, color:T.muted }}>
                {cell.cell_type}
              </span>
              {!cell.commons_thread_id && (
                <span style={{ fontSize:8, color:T.textDim }}>
                  internal
                </span>
              )}
              {cell.initiating_member && (
                <span style={{ fontSize:8, color:T.textSub, marginLeft:"auto" }}>
                  @{cell.initiating_member.handle}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
