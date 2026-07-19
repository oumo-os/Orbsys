"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { stfApi } from "@/lib/api";
import { T, Pill, Dot, BarMini, SectionHead } from "@/components/ui";

interface StfData {
  id: string;
  type: string;
  circle_name?: string;
  mandate: string;
  state: string;
  members?: { member_id: string; handle: string }[];
  commissioned_at?: string;
  deadline?: string;
  progress?: number;
  days_left?: number;
  days_total?: number;
  parent_cell_id?: string;
}

interface Metric {
  label: string;
  value: string;
  pct?: number | null;
}

interface LogEntry {
  entry: string;
  date: string;
}

export default function StfDetailPage() {
  const params = useParams();
  const stfId = params.id as string;
  const [stf, setStf] = useState<StfData | null>(null);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await stfApi.get(stfId);
      setStf(res.data);
    } catch { /* silent */ }
    setLoading(false);
  }, [stfId]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return <p style={{ color:T.muted, fontSize:11, fontFamily:T.mono, padding:20 }}>Loading…</p>;
  }
  if (!stf) {
    return <p style={{ color:T.muted, fontSize:11, fontFamily:T.mono, padding:20 }}>STF not found.</p>;
  }

  const progress = stf.progress ?? 0;
  const daysLeft = stf.days_left ?? 0;
  const daysTotal = stf.days_total ?? 46;
  const daysSpent = daysTotal - daysLeft;
  const timePct = Math.round((daysSpent / daysTotal) * 100);

  return (
    <div style={{ display:"flex", gap:20, flex:1 }}>
      <div style={{ flex:1, minWidth:0 }}>
        {/* STF Header */}
        <div style={{
          padding:"20px", borderRadius:8,
          border:`1px solid ${T.border}`, background:T.surface, marginBottom:20,
          position:"relative", overflow:"hidden",
        }}>
          <div style={{
            position:"absolute", top:0, left:0, right:0, height:2,
            background:`linear-gradient(90deg,${T.red},transparent)`,
          }}/>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
            <div>
              <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:6 }}>
                <Pill color={T.red} bg={`${T.red}15`}>⚑ {stf.type || "STF"}</Pill>
                <span style={{ fontSize:10, color:T.muted, fontFamily:T.mono }}>{stf.id.slice(0, 8)}</span>
              </div>
              <p style={{
                margin:"0 0 8px", fontSize:15, color:T.text, fontFamily:T.serif,
              }}>{stf.mandate}</p>
              <div style={{ display:"flex", gap:6 }}>
                {stf.circle_name && (
                  <Pill color={T.gold} bg={`${T.gold}15`}>↖ {stf.circle_name}</Pill>
                )}
                {stf.commissioned_at && stf.deadline && (
                  <Pill color={T.muted}>{stf.commissioned_at} → {stf.deadline}</Pill>
                )}
              </div>
            </div>
            <div style={{ textAlign:"right", flexShrink:0, marginLeft:16 }}>
              <p style={{
                margin:"0 0 4px", fontSize:28,
                color:daysLeft < 7 ? T.red : T.gold, fontFamily:T.mono,
              }}>{daysLeft}</p>
              <span style={{ fontSize:9, color:T.muted, fontFamily:T.mono }}>days remaining</span>
            </div>
          </div>
          <div style={{ marginTop:16 }}>
            <div style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
              <span style={{ fontSize:9, color:T.muted, fontFamily:T.mono }}>Work progress vs time elapsed</span>
              <span style={{ fontSize:9, color:T.gold, fontFamily:T.mono }}>
                {progress}% work · {timePct}% time
              </span>
            </div>
            <div style={{ height:3, background:T.border, borderRadius:2, marginBottom:3 }}>
              <div style={{ width:`${progress}%`, height:"100%", background:T.gold, borderRadius:2 }}/>
            </div>
            <div style={{ height:3, background:T.border, borderRadius:2 }}>
              <div style={{ width:`${timePct}%`, height:"100%", background:`${T.blue}60`, borderRadius:2 }}/>
            </div>
            <div style={{ display:"flex", gap:14, marginTop:4 }}>
              <div style={{ display:"flex", alignItems:"center", gap:4 }}>
                <div style={{ width:10, height:1.5, background:T.gold }}/>
                <span style={{ fontSize:8, color:T.muted, fontFamily:T.mono }}>work</span>
              </div>
              <div style={{ display:"flex", alignItems:"center", gap:4 }}>
                <div style={{ width:10, height:1.5, background:`${T.blue}60` }}/>
                <span style={{ fontSize:8, color:T.muted, fontFamily:T.mono }}>time</span>
              </div>
            </div>
          </div>
        </div>

        {/* Metrics */}
        {metrics.length > 0 && (
          <>
            <SectionHead label="Metrics"/>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:24 }}>
              {metrics.map(m => (
                <div key={m.label} style={{
                  padding:"14px", borderRadius:7,
                  border:`1px solid ${T.border}`, background:T.panel,
                }}>
                  <p style={{ margin:"0 0 6px", fontSize:10, color:T.muted, fontFamily:T.mono }}>{m.label}</p>
                  <p style={{ margin:0, fontSize:16, color:T.text, fontFamily:T.mono }}>{m.value}</p>
                  {m.pct != null && <div style={{ marginTop:8 }}><BarMini pct={m.pct} color={T.blue}/></div>}
                </div>
              ))}
            </div>
          </>
        )}

        {/* Audit Log */}
        {log.length > 0 && (
          <>
            <SectionHead label="Audit Log" sub="Tamper-evident record"/>
            {log.map((l, i) => (
              <div key={i} style={{
                padding:"14px 16px", borderRadius:7,
                border:`1px solid ${T.border}`, background:T.surface, marginBottom:8,
              }}>
                <p style={{
                  margin:"0 0 6px", fontSize:12, color:"#bbb",
                  fontFamily:T.serif, lineHeight:1.6,
                }}>{l.entry}</p>
                <span style={{ fontSize:9, color:T.muted, fontFamily:T.mono }}>{l.date}</span>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Right rail */}
      <div style={{ width:236, flexShrink:0 }}>
        {/* Members */}
        <SectionHead label="Members"/>
        {(stf.members || []).map((m, i) => (
          <div key={m.member_id} style={{
            display:"flex", alignItems:"center", gap:8,
            padding:"9px 0", borderBottom:`1px solid ${T.border}`,
          }}>
            <div style={{
              width:24, height:24, borderRadius:"50%",
              background:`${T.red}20`, border:`1px solid ${T.red}30`,
              display:"flex", alignItems:"center", justifyContent:"center",
              fontSize:10, color:T.red,
            }}>{m.handle[0]}</div>
            <span style={{ fontSize:11, color:T.textSub, fontFamily:T.serif }}>{m.handle}</span>
          </div>
        ))}

        {/* Quorum */}
        <div style={{ marginTop:24 }}>
          <SectionHead label="Quorum"/>
          <div style={{
            padding:"12px 14px", borderRadius:7,
            background:`${T.green}10`, border:`1px solid ${T.green}25`,
          }}>
            <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:4 }}>
              <Dot color={T.green}/>
              <span style={{ fontSize:11, color:T.green, fontFamily:T.mono }}>
                {(stf.members || []).length} members
              </span>
            </div>
            <p style={{
              margin:0, fontSize:10, color:`${T.green}88`,
              fontFamily:T.serif, fontStyle:"italic",
            }}>Active and participating.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
