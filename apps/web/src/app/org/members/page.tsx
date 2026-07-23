"use client";
import { useEffect, useState, useCallback } from "react";
import { membersApi } from "@/lib/api";

const T = {
  surface:"#080808", raised:"#0c0c0c", border:"#141414",
  dim:"#2a2a2a", muted:"#555555", textDim:"#3a3a3a",
  text:"#cccccc", textSub:"#777777",
  gold:"#c8a96e", goldDim:"#c8a96e22", green:"#5a8a6a",
  mono:"'DM Mono',monospace", serif:"'Lora',serif",
};

const STATE_COLOR: Record<string,string> = {
  active:T.green, probationary:T.gold,
  suspended:"#c87a6e", under_review:T.gold,
  inactive:T.muted, exited:T.muted,
};

interface Member {
  id:string; handle:string; display_name:string;
  current_state:string; joined_at:string;
}

interface Application {
  id:string; handle:string; display_name:string;
  status:string; created_at:string; motivation?:string;
}

export default function MembersPage() {
  const [tab,      setTab]      = useState<"members"|"applications">("members");
  const [members,  setMembers]  = useState<Member[]>([]);
  const [apps,     setApps]     = useState<Application[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [reviewing,setReviewing]= useState<string|null>(null);

  const loadMembers = useCallback(async () => {
    setLoading(true);
    try {
      if (tab==="members") {
        // GET /members — list all members
        const r = await membersApi.list({ page:1, page_size:100 });
        setMembers(r.data?.items ?? []);
      } else {
        const r = await membersApi.applications({ status:"pending", page_size:50 });
        setApps(r.data?.items ?? []);
      }
    } finally { setLoading(false); }
  }, [tab]);

  useEffect(()=>{ loadMembers(); },[loadMembers]);

  async function review(id:string, approve:boolean, note?:string) {
    setReviewing(id);
    try {
      await membersApi.reviewApplication(id, { approve, note });
      await loadMembers();
    } finally { setReviewing(null); }
  }

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%",
      border:`1px solid ${T.border}`, borderRadius:6, overflow:"hidden",
      background:T.surface }}>

      {/* Tabs */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
        padding:"9px 14px", borderBottom:`1px solid ${T.border}`, flexShrink:0 }}>
        <div style={{ display:"flex" }}>
          {(["members","applications"] as const).map(t=>(
            <button key={t} onClick={()=>setTab(t)} style={{
              padding:"4px 10px", background:"transparent", border:"none",
              cursor:"pointer", fontFamily:T.mono, fontSize:9,
              color:tab===t?T.gold:T.muted, letterSpacing:1, textTransform:"uppercase",
              borderBottom:`1px solid ${tab===t?T.gold:"transparent"}`,
            }}>{t}</button>
          ))}
        </div>
        <span style={{ fontSize:9, color:T.muted }}>
          {tab==="members" ? `${members.length} members` : `${apps.length} pending`}
        </span>
      </div>

      {/* Content */}
      <div style={{ flex:1, overflowY:"auto" }}>
        {loading
          ? <div style={{ padding:24, color:T.muted, fontSize:10, textAlign:"center" }}>Loading…</div>

          : tab==="members"
          ? members.length===0
            ? <div style={{ padding:24, color:T.muted, fontSize:10, textAlign:"center" }}>No members.</div>
            : members.map((m,i)=>(
            <div key={m.id} style={{
              padding:"10px 14px",
              borderBottom:i<members.length-1?`1px solid ${T.border}`:"none",
              display:"flex", justifyContent:"space-between", alignItems:"center",
            }}>
              <div>
                <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:2 }}>
                  <span style={{ fontSize:12, color:T.text, fontFamily:T.serif }}>
                    {m.display_name}
                  </span>
                  <span style={{ fontSize:9, color:T.muted }}>@{m.handle}</span>
                </div>
                <span style={{ fontSize:9, color:STATE_COLOR[m.current_state]??T.muted,
                  fontFamily:T.mono }}>{m.current_state}</span>
              </div>
              <span style={{ fontSize:8, color:T.textDim, fontFamily:T.mono }}>
                {new Date(m.joined_at).toLocaleDateString()}
              </span>
            </div>
          ))

          : apps.length===0
          ? <div style={{ padding:24, color:T.muted, fontSize:10, textAlign:"center" }}>
              No pending applications.
            </div>
          : apps.map((a,i)=>(
            <div key={a.id} style={{
              padding:"12px 14px",
              borderBottom:i<apps.length-1?`1px solid ${T.border}`:"none",
            }}>
              <div style={{ display:"flex", justifyContent:"space-between",
                marginBottom:6 }}>
                <div>
                  <div style={{ display:"flex", alignItems:"center", gap:8,
                    marginBottom:2 }}>
                    <span style={{ fontSize:12, color:T.text, fontFamily:T.serif }}>
                      {a.display_name}
                    </span>
                    <span style={{ fontSize:9, color:T.muted }}>@{a.handle}</span>
                  </div>
                  {a.motivation && (
                    <p style={{ margin:"4px 0 0", fontSize:10, color:T.textSub,
                      fontFamily:T.serif, lineHeight:1.5, maxWidth:500 }}>
                      {a.motivation}
                    </p>
                  )}
                </div>
                <span style={{ fontSize:8, color:T.textDim, fontFamily:T.mono,
                  flexShrink:0, marginLeft:16 }}>
                  {new Date(a.created_at).toLocaleDateString()}
                </span>
              </div>
              <div style={{ display:"flex", gap:6 }}>
                <button
                  onClick={()=>review(a.id, true)}
                  disabled={reviewing===a.id}
                  style={{ padding:"4px 12px", background:T.goldDim,
                    border:`1px solid ${T.gold}50`, borderRadius:4,
                    color:T.gold, fontFamily:T.mono, fontSize:9,
                    cursor:"pointer", letterSpacing:1,
                    opacity:reviewing===a.id?0.5:1 }}>
                  {reviewing===a.id?"…":"approve"}
                </button>
                <button
                  onClick={()=>review(a.id, false)}
                  disabled={reviewing===a.id}
                  style={{ padding:"4px 12px", background:"transparent",
                    border:`1px solid ${T.dim}`, borderRadius:4,
                    color:T.muted, fontFamily:T.mono, fontSize:9,
                    cursor:"pointer", letterSpacing:1,
                    opacity:reviewing===a.id?0.5:1 }}>
                  decline
                </button>
              </div>
            </div>
          ))
        }
      </div>
    </div>
  );
}
