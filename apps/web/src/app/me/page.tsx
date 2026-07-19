"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { accountApi, platformApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const T = {
  bg:"#050505", surface:"#080808", raised:"#0c0c0c",
  border:"#141414", dim:"#2a2a2a", muted:"#555555",
  text:"#cccccc", textSub:"#777777", textDim:"#3a3a3a",
  gold:"#c8a96e", goldDim:"#c8a96e22",
  mono:"'DM Mono',monospace", serif:"'Lora',serif",
};

interface OrgMembership {
  org_id:string; org_slug:string; org_name:string;
  member_id:string; display_name_org:string; current_state:string;
  joined_at:string|null;
}

export default function MeDashboard() {
  const router = useRouter();
  const { account, isAuthenticated, setOrgSession, logout } = useAuthStore();
  const [orgs,    setOrgs]    = useState<OrgMembership[]>([]);
  const [loading, setLoading] = useState(true);
  const [entering,setEntering]= useState<string|null>(null);

  useEffect(() => {
    if (!isAuthenticated) { router.replace("/auth/login"); return; }
    accountApi.myOrgs()
      .then(r => setOrgs(r.data?.items ?? []))
      .catch(()=>{})
      .finally(()=>setLoading(false));
  }, [isAuthenticated, router]);

  async function enterOrg(org: OrgMembership) {
    setEntering(org.org_id);
    try {
      const res = await platformApi.enterOrg(org.org_id);
      setOrgSession({
        id: org.member_id,
        handle: "",
        display_name: org.display_name_org,
        display_name_org: org.display_name_org,
        org_id: org.org_id,
        org_slug: org.org_slug,
        org_name: org.org_name,
        current_state: org.current_state,
      }, res.data.org_session_token);
      router.push("/org/commons");
    } finally { setEntering(null); }
  }

  const stateColor = (s:string) =>
    s==="active"?"#5a8a6a":s==="probationary"?T.gold:T.muted;

  return (
    <div style={{ minHeight:"100vh", background:T.bg,
      fontFamily:T.mono, color:T.text }}>

      {/* Header */}
      <div style={{
        borderBottom:`1px solid ${T.border}`,
        padding:"16px 24px",
        display:"flex", justifyContent:"space-between", alignItems:"center",
      }}>
        <div>
          <p style={{ margin:"0 0 2px", fontSize:9, color:T.muted,
            letterSpacing:3, textTransform:"uppercase" }}>PAAS · Orb Sys</p>
          <h1 style={{ margin:0, fontSize:18, fontFamily:T.serif,
            fontWeight:400, color:T.text }}>
            {account?.handle ? `@${account.handle}` : "My Account"}
          </h1>
        </div>
        <div style={{ display:"flex", gap:12, alignItems:"center" }}>
          <button
            onClick={()=>router.push("/setup")}
            style={{ background:"transparent", border:`1px solid ${T.dim}`,
              borderRadius:4, padding:"5px 12px", cursor:"pointer",
              fontFamily:T.mono, fontSize:9, color:T.textSub,
              letterSpacing:1, textTransform:"uppercase" }}>
            + new org
          </button>
          <button
            onClick={()=>{ logout(); router.replace("/auth/login"); }}
            style={{ background:"none", border:"none", cursor:"pointer",
              fontSize:9, color:T.muted, fontFamily:T.mono }}>
            sign out
          </button>
        </div>
      </div>

      <div style={{ maxWidth:640, margin:"0 auto", padding:"32px 24px" }}>

        {/* Org memberships */}
        <div style={{ marginBottom:32 }}>
          <p style={{ margin:"0 0 14px", fontSize:9, color:T.muted,
            letterSpacing:2, textTransform:"uppercase" }}>
            Organisation memberships
          </p>

          {loading ? (
            <p style={{ color:T.muted, fontSize:10 }}>Loading…</p>
          ) : orgs.length === 0 ? (
            <div style={{
              padding:"24px", border:`1px solid ${T.border}`,
              borderRadius:6, background:T.surface, textAlign:"center",
            }}>
              <p style={{ color:T.muted, fontSize:11, marginBottom:12 }}>
                You are not a member of any organisation.
              </p>
              <div style={{ display:"flex", gap:8, justifyContent:"center" }}>
                <button onClick={()=>router.push("/setup")}
                  style={{ padding:"6px 14px",
                    background:T.goldDim, border:`1px solid ${T.gold}50`,
                    borderRadius:4, color:T.gold, fontFamily:T.mono,
                    fontSize:9, cursor:"pointer", letterSpacing:1,
                    textTransform:"uppercase" }}>
                  Start an org →
                </button>
                <button onClick={()=>router.push("/discover")}
                  style={{ padding:"6px 14px", background:"transparent",
                    border:`1px solid ${T.dim}`, borderRadius:4,
                    color:T.muted, fontFamily:T.mono, fontSize:9,
                    cursor:"pointer", letterSpacing:1, textTransform:"uppercase" }}>
                  Browse orgs
                </button>
              </div>
            </div>
          ) : (
            <div style={{ border:`1px solid ${T.border}`, borderRadius:6,
              background:T.surface, overflow:"hidden" }}>
              {orgs.map((org, i) => (
                <div key={org.org_id} style={{
                  padding:"12px 16px",
                  borderBottom: i<orgs.length-1 ? `1px solid ${T.border}` : "none",
                  display:"flex", justifyContent:"space-between", alignItems:"center",
                }}>
                  <div>
                    <p style={{ margin:"0 0 2px", fontSize:12,
                      color:T.text, fontFamily:T.serif }}>
                      {org.org_name}
                    </p>
                    <p style={{ margin:0, fontSize:9, color:T.textSub }}>
                      {org.display_name_org} ·{" "}
                      <span style={{ color:stateColor(org.current_state) }}>
                        {org.current_state}
                      </span>
                    </p>
                  </div>
                  <button
                    onClick={()=>enterOrg(org)}
                    disabled={entering===org.org_id}
                    style={{
                      padding:"5px 12px",
                      background: entering===org.org_id ? T.goldDim : "transparent",
                      border:`1px solid ${entering===org.org_id?T.gold:T.dim}`,
                      borderRadius:4, color:entering===org.org_id?T.gold:T.textSub,
                      fontFamily:T.mono, fontSize:9, cursor:"pointer",
                      letterSpacing:1, textTransform:"uppercase",
                      transition:"all 0.15s",
                    }}>
                    {entering===org.org_id ? "entering…" : "enter →"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Account info */}
        {account && (
          <div style={{
            padding:"14px 16px", border:`1px solid ${T.border}`,
            borderRadius:6, background:T.surface,
          }}>
            <p style={{ margin:"0 0 10px", fontSize:9, color:T.muted,
              letterSpacing:2, textTransform:"uppercase" }}>Account</p>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"8px 16px" }}>
              {[
                ["Handle",     `@${account.handle}`],
                ["Legal name", account.legal_name ?? "—"],
              ].map(([label,val]) => (
                <div key={label}>
                  <p style={{ margin:"0 0 1px", fontSize:8, color:T.muted,
                    textTransform:"uppercase", letterSpacing:1 }}>{label}</p>
                  <p style={{ margin:0, fontSize:11, color:T.text }}>{val}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
