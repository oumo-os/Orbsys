"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { circlesApi } from "@/lib/api";
import { T, BarMini, SectionHead } from "@/components/ui";

interface Circle {
  id: string;
  name: string;
  description?: string;
  member_count: number;
  dissolved_at?: string | null;
}

export default function CirclesPage() {
  const router = useRouter();
  const [circles, setCircles] = useState<Circle[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await circlesApi.list();
      const d = res.data;
      setCircles(d?.items ?? d ?? []);
    } catch { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return <p style={{ color:T.muted, fontSize:11, fontFamily:T.mono, padding:20 }}>Loading…</p>;
  }

  return (
    <div style={{ display:"flex", gap:20, flex:1 }}>
      <div style={{ flex:1, minWidth:0 }}>
        <SectionHead label="Circles" sub="Organisation's governance circles"/>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
          {circles.map(c => (
            <div key={c.id}
              style={{
                padding:"14px", borderRadius:7,
                border:`1px solid ${T.border}`, background:T.panel, cursor:"pointer",
              }}
              onClick={() => router.push(`/org/circles/${c.id}`)}
              onMouseEnter={e => e.currentTarget.style.borderColor = T.border2}
              onMouseLeave={e => e.currentTarget.style.borderColor = T.border}
            >
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:6 }}>
                <span style={{ fontSize:9, color:T.muted, fontFamily:T.mono }}>
                  {c.member_count} members
                </span>
              </div>
              <p style={{
                margin:"0 0 10px", fontSize:13, color:"#bbb",
                fontFamily:T.serif, lineHeight:1.3,
              }}>{c.name}</p>
              {c.description && (
                <p style={{
                  margin:0, fontSize:10, color:T.textDim,
                  fontFamily:T.mono, lineHeight:1.5,
                  overflow:"hidden", textOverflow:"ellipsis",
                  display:"-webkit-box", WebkitLineClamp:2, WebkitBoxOrient:"vertical",
                }}>{c.description}</p>
              )}
            </div>
          ))}
        </div>
      </div>
      <div style={{ width:236, flexShrink:0 }}>
        <SectionHead label="Organisation"/>
        <p style={{ fontSize:10, color:T.muted, fontFamily:T.mono, lineHeight:1.6 }}>
          Circles govern dormains. Each circle holds mandate authority over assigned domains and manages Cell composition.
        </p>
      </div>
    </div>
  );
}
