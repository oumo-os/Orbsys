"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { accountApi, membersApi, circlesApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { T, Pill, BarMini, SectionHead, Dot } from "@/components/ui";

export default function MePage() {
  const router = useRouter();
  const { account, member, isAuthenticated, logout } = useAuthStore();
  const [orgs, setOrgs] = useState<any[]>([]);
  const [competences, setCompetences] = useState<any[]>([]);
  const [curiosities, setCuriosities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const orgsRes = await accountApi.myOrgs();
      setOrgs(orgsRes.data?.items ?? []);
    } catch { /* silent */ }
    try {
      const scoresRes = await membersApi.me();
      const d = scoresRes.data;
      setCompetences(d?.competence_scores ?? []);
    } catch { /* silent */ }
    try {
      const curRes = await membersApi.curiosities();
      setCuriosities(curRes.data ?? []);
    } catch { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!isAuthenticated) { router.replace("/auth/login"); return; }
    load();
  }, [isAuthenticated, load, router]);

  if (!isAuthenticated) return null;
  if (loading) {
    return <p style={{ color:T.muted, fontSize:11, fontFamily:T.mono, padding:20 }}>Loading…</p>;
  }

  return (
    <div style={{ display:"flex", gap:20 }}>
      <div style={{ flex:1, minWidth:0 }}>
        {/* Profile card */}
        <div style={{
          padding:"20px", borderRadius:8,
          border:`1px solid ${T.border}`, background:T.surface, marginBottom:20,
        }}>
          <div style={{ display:"flex", gap:16, alignItems:"flex-start" }}>
            <div style={{
              width:52, height:52, borderRadius:"50%",
              background:"linear-gradient(135deg,#2a3040,#1a2030)",
              border:`1px solid ${T.goldDim}`,
              display:"flex", alignItems:"center", justifyContent:"center",
              fontSize:20, color:T.gold, flexShrink:0,
            }}>{(account?.handle || member?.handle || "?")[0].toUpperCase()}</div>
            <div style={{ flex:1 }}>
              <h2 style={{
                margin:"0 0 4px", fontSize:18, color:T.text,
                fontFamily:T.serif, fontWeight:400,
              }}>{account?.handle || "User"}</h2>
              <p style={{
                margin:"0 0 8px", fontSize:10, color:T.muted, fontFamily:T.mono,
              }}>@{account?.handle || member?.handle} · {member?.current_state || "member"}</p>
              {member?.org_name && (
                <p style={{
                  margin:0, fontSize:12, color:T.textSub,
                  fontFamily:T.serif, lineHeight:1.65,
                }}>Member of {member.org_name}</p>
              )}
            </div>
          </div>
          {member?.current_state && (
            <div style={{
              display:"flex", flexWrap:"wrap", gap:6, marginTop:16,
              paddingTop:14, borderTop:`1px solid ${T.border}`,
            }}>
              <Pill color={T.gold} bg={`${T.gold}15`}>◎ {member.org_name || "Org"}</Pill>
              <Pill color={T.muted}>State: {member.current_state}</Pill>
            </div>
          )}
        </div>

        {/* Competences */}
        {competences.length > 0 && (
          <>
            <SectionHead label="Competence Scores" sub="Wh (hard credentials) · Ws (contribution)"/>
            <div style={{ marginBottom:24 }}>
              {competences.map((c: any) => (
                <div key={c.dormain_name || c.id} style={{
                  display:"flex", alignItems:"center", gap:10, padding:"8px 0",
                  borderBottom:`1px solid ${T.border}`,
                }}>
                  <span style={{ fontSize:10, color:T.muted, fontFamily:T.mono, minWidth:120 }}>
                    {c.dormain_name || c.name}
                  </span>
                  <BarMini pct={Math.min(((c.w_s || 0) / 2000) * 100, 100)} color={T.green}/>
                  <span style={{ fontSize:9, color:T.gold, fontFamily:T.mono, minWidth:40, textAlign:"right" }}>
                    Ws {Math.round(c.w_s || 0)}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Curiosities */}
        {curiosities.length > 0 && (
          <>
            <SectionHead label="Curiosity Signals" sub="Self-declared · shapes matching, never vote weight"/>
            {curiosities.map((c: any) => (
              <div key={c.tag || c.id} style={{
                display:"flex", alignItems:"center", gap:10, padding:"6px 0",
              }}>
                <span style={{ fontSize:10, color:T.muted, fontFamily:T.mono, minWidth:210 }}>
                  #{c.tag || c.name}
                </span>
                <BarMini pct={(c.weight || 0) * 100} color={T.blue}/>
                <span style={{ fontSize:9, color:T.gold, fontFamily:T.mono, minWidth:30, textAlign:"right" }}>
                  {Math.round((c.weight || 0) * 100)}%
                </span>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Right rail */}
      <div style={{ width:236, flexShrink:0 }}>
        <SectionHead label="Memberships"/>
        {orgs.map((o: any) => (
          <div key={o.org_id} style={{
            padding:"10px 0", borderBottom:`1px solid ${T.border}`, cursor:"pointer",
          }} onClick={() => {
            if (orgs.length === 1) router.push("/org/commons");
          }}>
            <p style={{ margin:"0 0 4px", fontSize:12, color:T.text, fontFamily:T.serif }}>{o.org_name || o.org_slug}</p>
            <div style={{ display:"flex", justifyContent:"space-between" }}>
              <span style={{ fontSize:9, color:T.muted, fontFamily:T.mono }}>@{o.handle}</span>
              <span style={{ fontSize:9, color:T.gold, fontFamily:T.mono }}>{o.current_state}</span>
            </div>
          </div>
        ))}
        {orgs.length > 1 && (
          <p style={{ fontSize:9, color:T.muted, fontFamily:T.mono, marginTop:12 }}>
            Switch org via sidebar context.
          </p>
        )}

        <div style={{ marginTop:24 }}>
          <SectionHead label="Quick Actions"/>
          {[
            ["View Commons", "/org/commons"],
            ["View Circles", "/org/circles"],
            ["View Ledger", "/org/ledger"],
          ].map(([label, href]) => (
            <button key={href} onClick={() => router.push(href)} style={{
              display:"block", width:"100%", textAlign:"left",
              padding:"8px 0", borderBottom:`1px solid ${T.border}`,
              border:"none", background:"none", cursor:"pointer",
              fontSize:11, color:T.textSub, fontFamily:T.serif,
            }}>{label}</button>
          ))}
        </div>
      </div>
    </div>
  );
}
