"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { orgApi, circlesApi, motionsApi, stfApi } from "@/lib/api";
import { T, SectionHead, BarMini, StatusPill } from "@/components/ui";

interface OrgData {
  name: string;
  purpose?: string;
  slug: string;
}

interface Circle {
  id: string;
  name: string;
  description?: string;
  member_count?: number;
}

interface Motion {
  id: string;
  title: string;
  circle_name?: string;
  state: string;
  created_at: string;
}

export default function OrgPage() {
  const router = useRouter();
  const [org, setOrg] = useState<OrgData | null>(null);
  const [circles, setCircles] = useState<Circle[]>([]);
  const [motions, setMotions] = useState<Motion[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [orgRes, circRes, motRes] = await Promise.allSettled([
        orgApi.get(),
        circlesApi.list(),
        motionsApi.list({ page_size: 10 }),
      ]);
      if (orgRes.status === "fulfilled") setOrg(orgRes.value.data);
      if (circRes.status === "fulfilled") {
        const d = circRes.value.data;
        setCircles(d?.items ?? d ?? []);
      }
      if (motRes.status === "fulfilled") {
        const d = motRes.value.data;
        setMotions(d?.items ?? d ?? []);
      }
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
        {/* Org profile */}
        {org && (
          <div style={{
            padding:"20px", borderRadius:8,
            border:`1px solid ${T.border}`, background:T.surface, marginBottom:20,
          }}>
            <div style={{ display:"flex", alignItems:"flex-start", gap:14 }}>
              <div style={{
                width:44, height:44, borderRadius:8,
                background:"linear-gradient(135deg,#1a2030,#0a1020)",
                border:`1px solid ${T.goldDim}`,
                display:"flex", alignItems:"center", justifyContent:"center",
                fontSize:18, color:T.gold, flexShrink:0,
              }}>⊕</div>
              <div>
                <h2 style={{
                  margin:"0 0 6px", fontSize:17, color:T.text,
                  fontFamily:T.serif, fontWeight:400,
                }}>{org.name}</h2>
                <p style={{
                  margin:0, fontSize:12, color:T.textSub,
                  fontFamily:T.serif, lineHeight:1.65,
                }}>{org.purpose || "Organisation codex · universally readable"}</p>
              </div>
            </div>
          </div>
        )}

        {/* Circles */}
        <SectionHead label="Circles"/>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:28 }}>
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
                  {c.member_count ?? 0} members
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

        {/* Active motions */}
        <SectionHead label="Active Motions" sub="Proposals under deliberation · not yet adopted"/>
        {motions.length === 0 ? (
          <p style={{ color:T.muted, fontSize:11, fontFamily:T.mono, padding:"12px 0" }}>No active motions.</p>
        ) : (
          motions.map(m => (
            <div key={m.id}
              style={{
                display:"flex", alignItems:"center", gap:12,
                padding:"11px 0", borderBottom:`1px solid ${T.border}`,
              }}
            >
              <StatusPill status={m.state}/>
              <p style={{
                margin:0, flex:1, fontSize:12, color:"#bbb", fontFamily:T.serif,
              }}>{m.title}</p>
              <span style={{ fontSize:10, color:T.muted, fontFamily:T.mono }}>{m.circle_name}</span>
              <span style={{ fontSize:9, color:T.muted, fontFamily:T.mono }}>
                {new Date(m.created_at).toLocaleDateString()}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Right rail */}
      <div style={{ width:236, flexShrink:0 }}>
        <SectionHead label="Org Health"/>
        {[
          ["Active motions", motions.length],
          ["Open circles", circles.length],
        ].map(([label, value]) => (
          <div key={label} style={{
            display:"flex", justifyContent:"space-between",
            padding:"9px 0", borderBottom:`1px solid ${T.border}`,
          }}>
            <span style={{ fontSize:11, color:T.textSub, fontFamily:T.serif }}>{label}</span>
            <span style={{ fontSize:13, color:T.gold, fontFamily:T.mono }}>{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
