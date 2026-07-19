"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { stfApi } from "@/lib/api";

const T = {
  bg:"#050505", surface:"#080808", raised:"#0c0c0c",
  border:"#141414", dim:"#2a2a2a", muted:"#555555",
  text:"#cccccc", textSub:"#777777", textDim:"#3a3a3a",
  gold:"#c8a96e", goldDim:"#c8a96e22", green:"#5a8a6a",
  mono:"'DM Mono',monospace", serif:"'Lora',serif",
};

const TYPE_LABELS: Record<string,string> = {
  astf:"aSTF", xstf:"xSTF", vstf:"vSTF", jstf:"jSTF",
  periodic_astf:"p-aSTF", astf_periodic:"p-aSTF",
};
const STATE_COLOR: Record<string,string> = {
  active:T.green, completed:T.muted, pending:T.gold,
};

interface STFInstance {
  id:string; stf_type:string; rubric_type?:string;
  mandate:string; state:string;
  commissioned_at:string; deadline_at?:string|null;
  aggregate_verdict?:string|null;
}

function TimeAgo({ iso }:{ iso:string }) {
  const d = (Date.now()-new Date(iso).getTime())/1000;
  return <span style={{color:T.muted,fontSize:9}}>
    {d<60?`${Math.floor(d)}s`:d<3600?`${Math.floor(d/60)}m`:d<86400?`${Math.floor(d/3600)}h`:`${Math.floor(d/86400)}d`}
  </span>;
}

export default function STFPage() {
  const router = useRouter();
  const [instances, setInstances] = useState<STFInstance[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [filter,    setFilter]    = useState<"active"|"all">("active");

  useEffect(()=>{
    stfApi.list(filter==="active"?{state:"active"}:undefined)
      .then(r=>setInstances(r.data?.items ?? []))
      .catch(()=>{})
      .finally(()=>setLoading(false));
  },[filter]);

  const verdictColor = (v:string|null|undefined) =>
    v==="approve"||v==="healthy"?T.green:v==="reject"||v==="concern"?"#c87a6e":T.gold;

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%",
      border:`1px solid ${T.border}`, borderRadius:6, overflow:"hidden",
      background:T.surface }}>

      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
        padding:"9px 14px", borderBottom:`1px solid ${T.border}`, flexShrink:0 }}>
        <div style={{ display:"flex" }}>
          {(["active","all"] as const).map(f=>(
            <button key={f} onClick={()=>setFilter(f)} style={{
              padding:"4px 10px", background:"transparent", border:"none",
              cursor:"pointer", fontFamily:T.mono, fontSize:9,
              color:filter===f?T.gold:T.muted, letterSpacing:1, textTransform:"uppercase",
              borderBottom:`1px solid ${filter===f?T.gold:"transparent"}`,
            }}>{f}</button>
          ))}
        </div>
        <span style={{ fontSize:9, color:T.muted }}>
          {instances.length} panel{instances.length!==1?"s":""}
        </span>
      </div>

      <div style={{ flex:1, overflowY:"auto" }}>
        {loading
          ? <div style={{ padding:24, color:T.muted, fontSize:10, textAlign:"center" }}>Loading…</div>
          : instances.length===0
          ? <div style={{ padding:24, color:T.muted, fontSize:10, textAlign:"center" }}>No STF panels.</div>
          : instances.map((s,i)=>(
          <div key={s.id}
            onClick={()=>router.push(`/org/stf/${s.id}`)}
            style={{
              padding:"11px 14px",
              borderBottom:i<instances.length-1?`1px solid ${T.border}`:"none",
              cursor:"pointer",
            }}
            onMouseEnter={e=>(e.currentTarget.style.background=T.raised)}
            onMouseLeave={e=>(e.currentTarget.style.background="transparent")}
          >
            <div style={{ display:"flex", justifyContent:"space-between",
              alignItems:"flex-start", marginBottom:4 }}>
              <div style={{ display:"flex", alignItems:"center", gap:6, flex:1 }}>
                <span style={{
                  fontSize:7, padding:"1px 5px", borderRadius:3,
                  background:T.raised, border:`1px solid ${T.border}`,
                  color:T.gold, fontFamily:T.mono, letterSpacing:1,
                  textTransform:"uppercase", flexShrink:0,
                }}>
                  {TYPE_LABELS[s.rubric_type??s.stf_type]??s.stf_type}
                </span>
                <span style={{ fontSize:11, color:T.text, fontFamily:T.serif,
                  lineHeight:1.4 }}>
                  {s.mandate.slice(0,90)}{s.mandate.length>90?"…":""}
                </span>
              </div>
              <span style={{ fontSize:9, color:STATE_COLOR[s.state]??T.muted,
                fontFamily:T.mono, flexShrink:0, marginLeft:8 }}>
                {s.state}
              </span>
            </div>
            <div style={{ display:"flex", gap:12, alignItems:"center" }}>
              <TimeAgo iso={s.commissioned_at} />
              {s.deadline_at && (
                <span style={{ fontSize:8, color:T.textSub }}>
                  due <TimeAgo iso={s.deadline_at} />
                </span>
              )}
              {s.aggregate_verdict && (
                <span style={{ fontSize:8, color:verdictColor(s.aggregate_verdict),
                  fontFamily:T.mono, marginLeft:"auto" }}>
                  {s.aggregate_verdict}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
