"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { circlesApi } from "@/lib/api";

const T = {
  bg:"#050505", surface:"#080808", raised:"#0c0c0c",
  border:"#141414", dim:"#2a2a2a", muted:"#555555",
  text:"#cccccc", textSub:"#777777", textDim:"#3a3a3a",
  gold:"#c8a96e", goldDim:"#c8a96e22",
  mono:"'DM Mono',monospace", serif:"'Lora',serif",
};

interface DormainRef { id:string; name:string; }
interface Circle {
  id:string; name:string; description?:string;
  dormains?:DormainRef[]; member_count?:number;
  founding_circle?:boolean; dissolved_at?:string|null;
}

export default function CirclesPage() {
  const router = useRouter();
  const [circles, setCircles] = useState<Circle[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(()=>{
    circlesApi.list()
      .then(r=>setCircles(r.data?.items ?? r.data ?? []))
      .catch(()=>{})
      .finally(()=>setLoading(false));
  },[]);

  const active   = circles.filter(c=>!c.dissolved_at && !c.founding_circle);
  const founding = circles.filter(c=>!c.dissolved_at &&  c.founding_circle);
  const dissolved= circles.filter(c=> c.dissolved_at);

  function Section({ title, items }: { title:string; items:Circle[] }) {
    if (!items.length) return null;
    return (
      <div style={{ marginBottom:24 }}>
        <p style={{ margin:"0 0 8px", fontSize:8, color:T.muted,
          letterSpacing:2, textTransform:"uppercase" }}>{title}</p>
        <div style={{ border:`1px solid ${T.border}`, borderRadius:6,
          background:T.surface, overflow:"hidden" }}>
          {items.map((c,i)=>(
            <div key={c.id}
              onClick={()=>router.push(`/org/circles/${c.id}`)}
              style={{
                padding:"11px 14px",
                borderBottom:i<items.length-1?`1px solid ${T.border}`:"none",
                cursor:"pointer", transition:"background 0.1s",
              }}
              onMouseEnter={e=>(e.currentTarget.style.background=T.raised)}
              onMouseLeave={e=>(e.currentTarget.style.background="transparent")}
            >
              <div style={{ display:"flex", justifyContent:"space-between",
                marginBottom:4 }}>
                <span style={{ fontSize:12, color:T.text, fontFamily:T.serif }}>
                  {c.name}
                </span>
                <span style={{ fontSize:9, color:T.muted, fontFamily:T.mono }}>
                  {c.member_count ?? 0} members
                </span>
              </div>
              {c.description && (
                <p style={{ margin:"0 0 5px", fontSize:10, color:T.textSub,
                  fontFamily:T.serif, lineHeight:1.5 }}>
                  {c.description}
                </p>
              )}
              {(c.dormains?.length ?? 0) > 0 && (
                <div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>
                  {(c.dormains??[]).map(d=>(
                    <span key={d.id} style={{
                      fontSize:8, padding:"1px 6px", borderRadius:10,
                      background:T.goldDim, border:`1px solid ${T.gold}30`,
                      color:T.gold, fontFamily:T.mono,
                    }}>{d.name}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth:700 }}>
      {loading
        ? <p style={{ color:T.muted, fontSize:10 }}>Loading…</p>
        : <>
            <Section title="Circles" items={active} />
            <Section title="Founding Circle" items={founding} />
            <Section title="Dissolved" items={dissolved} />
          </>
      }
    </div>
  );
}
