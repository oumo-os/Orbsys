"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { circlesApi, cellsApi } from "@/lib/api";
import { T, Pill, Dot, BarMini, SectionHead, DomainTag, StatusPill } from "@/components/ui";

interface CircleData {
  id: string;
  org_id: string;
  name: string;
  description?: string;
  tenets?: string;
  founding_circle: boolean;
  member_count: number;
  created_at: string;
  dissolved_at?: string | null;
  dormains: { dormain: { id: string; name: string }; mandate_type: string }[];
}

interface Member {
  member: { id: string; handle: string; display_name: string };
  joined_at: string;
  current_state: string;
  primary_dormain_ws?: number | null;
}

interface Cell {
  id: string;
  title: string;
  state: string;
  participants?: number;
}

export default function CircleDetailPage() {
  const params = useParams();
  const router = useRouter();
  const circleId = params.id as string;
  const [circle, setCircle] = useState<CircleData | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [cells, setCells] = useState<Cell[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [cRes, mRes] = await Promise.allSettled([
        circlesApi.get(circleId),
        circlesApi.members(circleId),
      ]);
      if (cRes.status === "fulfilled") setCircle(cRes.value.data);
      if (mRes.status === "fulfilled") {
        const d = mRes.value.data;
        setMembers(d?.items ?? d ?? []);
      }
      try {
        const cellRes = await cellsApi.list({ circle_id: circleId });
        const cd = cellRes.data;
        setCells(cd?.items ?? cd ?? []);
      } catch { /* silent */ }
    } catch { /* silent */ }
    setLoading(false);
  }, [circleId]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return <p style={{ color:T.muted, fontSize:11, fontFamily:T.mono, padding:20 }}>Loading…</p>;
  }
  if (!circle) {
    return <p style={{ color:T.muted, fontSize:11, fontFamily:T.mono, padding:20 }}>Circle not found.</p>;
  }

  const domains = circle.dormains || [];
  const primaryDomains = domains.filter(d => d.mandate_type === "primary");

  return (
    <div style={{ display:"flex", gap:20, flex:1 }}>
      <div style={{ flex:1, minWidth:0 }}>
        {/* Circle profile */}
        <div style={{
          padding:"16px 20px", borderRadius:8,
          border:`1px solid ${T.border}`, background:T.surface, marginBottom:20,
        }}>
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
            <div style={{ width:8, height:8, borderRadius:"50%", background:T.gold }}/>
            <h2 style={{
              margin:0, fontSize:16, color:T.text, fontFamily:T.serif, fontWeight:400,
            }}>{circle.name}</h2>
            <Pill color={T.gold} bg={`${T.gold}15`}>{circle.member_count} members</Pill>
          </div>
          {circle.description && (
            <p style={{
              margin:"0 0 10px", fontSize:12, color:T.textSub,
              fontFamily:T.serif, lineHeight:1.65,
            }}>{circle.description}</p>
          )}
          {circle.tenets && (
            <p style={{
              margin:"0 0 10px", fontSize:11, color:T.textDim,
              fontFamily:T.serif, lineHeight:1.6, fontStyle:"italic",
            }}>&ldquo;{circle.tenets}&rdquo;</p>
          )}
          <div style={{ display:"flex", gap:6 }}>
            {domains.map(d => (
              <DomainTag key={d.dormain.id} d={d.dormain.name} w={0.4}/>
            ))}
          </div>
        </div>

        {/* Members */}
        <SectionHead label="Members"/>
        <div style={{ marginBottom:28 }}>
          {members.map(cm => (
            <div key={cm.member.id} style={{
              display:"flex", alignItems:"center", gap:8,
              padding:"9px 0", borderBottom:`1px solid ${T.border}`,
            }}>
              <div style={{
                width:24, height:24, borderRadius:"50%",
                background:`${T.blue}20`,
                display:"flex", alignItems:"center", justifyContent:"center",
                fontSize:10, color:T.blue,
              }}>{cm.member.handle[0]}</div>
              <div style={{ flex:1 }}>
                <span style={{ fontSize:11, color:T.textSub, fontFamily:T.serif }}>
                  {cm.member.display_name || cm.member.handle}
                </span>
                <span style={{ fontSize:9, color:T.muted, fontFamily:T.mono, marginLeft:6 }}>
                  @{cm.member.handle}
                </span>
              </div>
              <StatusPill status={cm.current_state}/>
              {cm.primary_dormain_ws != null && (
                <span style={{ fontSize:9, color:T.gold, fontFamily:T.mono }}>
                  Ws {Math.round(cm.primary_dormain_ws)}
                </span>
              )}
            </div>
          ))}
          {members.length === 0 && (
            <p style={{ color:T.muted, fontSize:11, fontFamily:T.mono, padding:"12px 0" }}>No members.</p>
          )}
        </div>

        {/* Cells */}
        {cells.length > 0 && (
          <>
            <SectionHead label="Circle Cells" sub="Motions and special business"/>
            {cells.map(c => (
              <div key={c.id}
                style={{
                  padding:"14px 16px", borderRadius:7,
                  border:`1px solid ${T.border}`, background:T.panel, marginBottom:7, cursor:"pointer",
                }}
                onClick={() => router.push(`/org/cells/${c.id}`)}
                onMouseEnter={e => e.currentTarget.style.borderColor = T.border2}
                onMouseLeave={e => e.currentTarget.style.borderColor = T.border}
              >
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <p style={{ margin:0, fontSize:13, color:"#bbb", fontFamily:T.serif }}>{c.title}</p>
                  <StatusPill status={c.state}/>
                </div>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Right rail */}
      <div style={{ width:236, flexShrink:0 }}>
        <SectionHead label="Circle Info"/>
        <div style={{
          padding:"12px 14px", borderRadius:7,
          border:`1px solid ${T.border}`, background:T.surface, marginBottom:16,
        }}>
          <div style={{ display:"flex", justifyContent:"space-between", marginBottom:6 }}>
            <span style={{ fontSize:9, color:T.muted, fontFamily:T.mono }}>Founded</span>
            <span style={{ fontSize:9, color:T.textSub, fontFamily:T.mono }}>
              {new Date(circle.created_at).toLocaleDateString()}
            </span>
          </div>
          <div style={{ display:"flex", justifyContent:"space-between", marginBottom:6 }}>
            <span style={{ fontSize:9, color:T.muted, fontFamily:T.mono }}>Members</span>
            <span style={{ fontSize:9, color:T.gold, fontFamily:T.mono }}>{circle.member_count}</span>
          </div>
          <div style={{ display:"flex", justifyContent:"space-between" }}>
            <span style={{ fontSize:9, color:T.muted, fontFamily:T.mono }}>Domains</span>
            <span style={{ fontSize:9, color:T.gold, fontFamily:T.mono }}>{domains.length}</span>
          </div>
        </div>

        {primaryDomains.length > 0 && (
          <>
            <SectionHead label="Mandate Domains"/>
            {primaryDomains.map(d => (
              <div key={d.dormain.id} style={{
                padding:"7px 0", borderBottom:`1px solid ${T.border}`,
              }}>
                <span style={{ fontSize:10, color:T.textSub, fontFamily:T.mono }}>{d.dormain.name}</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
