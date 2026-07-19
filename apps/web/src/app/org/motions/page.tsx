"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motionsApi } from "@/lib/api";

const T = {
  bg:"#050505", surface:"#080808", raised:"#0c0c0c",
  border:"#141414", dim:"#2a2a2a", muted:"#555555",
  text:"#cccccc", textSub:"#777777",
  gold:"#c8a96e", goldDim:"#c8a96e22", green:"#5a8a6a",
  mono:"'DM Mono',monospace", serif:"'Lora',serif",
};

const STATE_COLOR: Record<string,string> = {
  draft:T.muted, voted:T.gold, approved:T.green,
  rejected:"#c87a6e", enacted_locked:T.green,
  revision_requested:T.gold, contested:"#c87a6e",
};

const TYPE_SHORT: Record<string,string> = {
  sys_bound:"sys", non_system:"dir", hybrid:"hyb",
};

interface Motion {
  id:string; motion_type:string; state:string;
  directive?:{body:string}; created_at:string;
  filed_by?:{handle:string};
}

function TimeAgo({ iso }:{ iso:string }) {
  const d=(Date.now()-new Date(iso).getTime())/1000;
  return <span style={{color:T.muted,fontSize:9}}>
    {d<60?`${Math.floor(d)}s`:d<3600?`${Math.floor(d/60)}m`:d<86400?`${Math.floor(d/3600)}h`:`${Math.floor(d/86400)}d`}
  </span>;
}

export default function MotionsPage() {
  const router = useRouter();
  const [motions, setMotions] = useState<Motion[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter,  setFilter]  = useState<"active"|"enacted"|"all">("active");

  useEffect(()=>{
    const params = filter==="active"
      ? { state:"voted", page_size:50 }
      : filter==="enacted"
      ? { state:"enacted_locked", page_size:50 }
      : { page_size:50 };
    motionsApi.list(params)
      .then(r=>setMotions(r.data?.items ?? []))
      .catch(()=>{})
      .finally(()=>setLoading(false));
  },[filter]);

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%",
      border:`1px solid ${T.border}`, borderRadius:6, overflow:"hidden",
      background:T.surface }}>

      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
        padding:"9px 14px", borderBottom:`1px solid ${T.border}`, flexShrink:0 }}>
        <div style={{ display:"flex" }}>
          {(["active","enacted","all"] as const).map(f=>(
            <button key={f} onClick={()=>setFilter(f)} style={{
              padding:"4px 10px", background:"transparent", border:"none",
              cursor:"pointer", fontFamily:T.mono, fontSize:9,
              color:filter===f?T.gold:T.muted, letterSpacing:1, textTransform:"uppercase",
              borderBottom:`1px solid ${filter===f?T.gold:"transparent"}`,
            }}>{f}</button>
          ))}
        </div>
        <span style={{ fontSize:9, color:T.muted }}>{motions.length} motion{motions.length!==1?"s":""}</span>
      </div>

      <div style={{ flex:1, overflowY:"auto" }}>
        {loading
          ? <div style={{ padding:24, color:T.muted, fontSize:10, textAlign:"center" }}>Loading…</div>
          : motions.length===0
          ? <div style={{ padding:24, color:T.muted, fontSize:10, textAlign:"center" }}>No motions.</div>
          : motions.map((m,i)=>(
          <div key={m.id} onClick={()=>router.push(`/org/motions/${m.id}`)}
            style={{ padding:"11px 14px",
              borderBottom:i<motions.length-1?`1px solid ${T.border}`:"none",
              cursor:"pointer" }}
            onMouseEnter={e=>(e.currentTarget.style.background=T.raised)}
            onMouseLeave={e=>(e.currentTarget.style.background="transparent")}>
            <div style={{ display:"flex", justifyContent:"space-between",
              alignItems:"flex-start", marginBottom:4 }}>
              <div style={{ display:"flex", alignItems:"center", gap:6, flex:1 }}>
                <span style={{ fontSize:7, padding:"1px 5px", borderRadius:3,
                  background:T.raised, border:`1px solid ${T.border}`,
                  color:T.gold, fontFamily:T.mono, letterSpacing:1,
                  textTransform:"uppercase", flexShrink:0 }}>
                  {TYPE_SHORT[m.motion_type]??m.motion_type}
                </span>
                <span style={{ fontSize:11, color:T.text, fontFamily:T.serif,
                  lineHeight:1.4 }}>
                  {m.directive?.body?.slice(0,90) ?? `Motion ${m.id.slice(0,8)}`}
                  {(m.directive?.body?.length??0)>90?"…":""}
                </span>
              </div>
              <span style={{ fontSize:9, fontFamily:T.mono, flexShrink:0, marginLeft:8,
                color:STATE_COLOR[m.state]??T.muted }}>
                {m.state.replace("_"," ")}
              </span>
            </div>
            <div style={{ display:"flex", gap:12 }}>
              <TimeAgo iso={m.created_at} />
              {m.filed_by && (
                <span style={{ fontSize:9, color:T.textSub }}>@{m.filed_by.handle}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
