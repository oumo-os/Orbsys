"use client";
import { useEffect, useState } from "react";
import { ledgerApi } from "@/lib/api";

const T = {
  surface:"#080808", raised:"#0c0c0c", border:"#141414",
  dim:"#2a2a2a", muted:"#555555", textDim:"#3a3a3a",
  text:"#cccccc", textSub:"#777777",
  gold:"#c8a96e", goldDim:"#c8a96e22", green:"#5a8a6a",
  mono:"'DM Mono',monospace", serif:"'Lora',serif",
};

interface LedgerEvent {
  id:string; event_type:string; subject_type:string;
  event_hash:string; prev_hash:string; created_at:string;
  payload?:Record<string,unknown>;
}

interface VerifyResult { status:string; verified_events:number; first_broken_event_id?:string; }

export default function LedgerPage() {
  const [events,  setEvents]  = useState<LedgerEvent[]>([]);
  const [verify,  setVerify]  = useState<VerifyResult|null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded,setExpanded]= useState<string|null>(null);
  const [checking,setChecking]= useState(false);

  useEffect(()=>{
    ledgerApi.events({ page:1, page_size:50 })
      .then(r=>setEvents(r.data?.items ?? []))
      .catch(()=>{})
      .finally(()=>setLoading(false));
  },[]);

  async function checkChain() {
    setChecking(true);
    try {
      const r = await ledgerApi.verify();
      setVerify(r.data);
    } finally { setChecking(false); }
  }

  const chainOk = verify?.status==="ok";

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%",
      border:`1px solid ${T.border}`, borderRadius:6, overflow:"hidden",
      background:T.surface }}>

      {/* Header */}
      <div style={{ padding:"9px 14px", borderBottom:`1px solid ${T.border}`,
        display:"flex", justifyContent:"space-between", alignItems:"center",
        flexShrink:0 }}>
        <span style={{ fontSize:9, color:T.muted, letterSpacing:2,
          textTransform:"uppercase" }}>Integrity Ledger</span>
        <div style={{ display:"flex", gap:8, alignItems:"center" }}>
          {verify && (
            <span style={{ fontSize:9, fontFamily:T.mono,
              color:chainOk?T.green:"#c87a6e" }}>
              {chainOk?`✓ ${verify.verified_events} events clean`:"✗ chain broken"}
            </span>
          )}
          <button onClick={checkChain} disabled={checking} style={{
            padding:"3px 10px", background:"transparent",
            border:`1px solid ${T.dim}`, borderRadius:4,
            cursor:"pointer", fontFamily:T.mono, fontSize:8,
            color:T.muted, letterSpacing:1, textTransform:"uppercase",
            opacity:checking?0.5:1,
          }}>
            {checking?"checking…":"verify chain"}
          </button>
        </div>
      </div>

      {/* Events */}
      <div style={{ flex:1, overflowY:"auto" }}>
        {loading
          ? <div style={{ padding:24, color:T.muted, fontSize:10, textAlign:"center" }}>Loading…</div>
          : events.map((ev,i)=>(
          <div key={ev.id}
            style={{ borderBottom:i<events.length-1?`1px solid ${T.border}`:"none" }}>
            <div onClick={()=>setExpanded(e=>e===ev.id?null:ev.id)}
              style={{ padding:"9px 14px", cursor:"pointer",
                display:"flex", justifyContent:"space-between", alignItems:"center" }}
              onMouseEnter={e=>(e.currentTarget.style.background=T.raised)}
              onMouseLeave={e=>(e.currentTarget.style.background="transparent")}>
              <div style={{ display:"flex", gap:8, alignItems:"center" }}>
                <span style={{ fontSize:8, color:T.gold, fontFamily:T.mono,
                  letterSpacing:0.5 }}>
                  {ev.event_type.replace(/_/g," ")}
                </span>
                <span style={{ fontSize:8, color:T.muted }}>
                  {ev.subject_type}
                </span>
              </div>
              <div style={{ display:"flex", gap:12, alignItems:"center" }}>
                <span style={{ fontSize:8, color:T.textDim, fontFamily:T.mono }}>
                  {ev.event_hash.slice(0,8)}…
                </span>
                <span style={{ fontSize:8, color:T.muted }}>
                  {new Date(ev.created_at).toLocaleTimeString()}
                </span>
              </div>
            </div>
            {expanded===ev.id && (
              <div style={{ padding:"8px 14px 12px", background:T.raised,
                borderTop:`1px solid ${T.border}` }}>
                <div style={{ display:"grid", gridTemplateColumns:"80px 1fr", gap:"4px 12px",
                  fontFamily:T.mono, fontSize:9 }}>
                  {[
                    ["id",        ev.id],
                    ["hash",      ev.event_hash],
                    ["prev",      ev.prev_hash],
                    ["created",   new Date(ev.created_at).toISOString()],
                  ].map(([k,v])=>(
                    <>
                      <span key={k+"k"} style={{ color:T.muted }}>{k}</span>
                      <span key={k+"v"} style={{ color:T.textSub,
                        wordBreak:"break-all" }}>{v}</span>
                    </>
                  ))}
                  {ev.payload && (
                    <>
                      <span style={{ color:T.muted, alignSelf:"start" }}>payload</span>
                      <pre style={{ color:T.textSub, fontSize:8, margin:0,
                        whiteSpace:"pre-wrap", wordBreak:"break-all" }}>
                        {JSON.stringify(ev.payload, null, 2)}
                      </pre>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
