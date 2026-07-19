"use client";
import { useEffect, useState } from "react";
import { competenceApi } from "@/lib/api";

const T = {
  surface:"#080808", raised:"#0c0c0c", border:"#141414",
  dim:"#2a2a2a", muted:"#555555", textDim:"#3a3a3a",
  text:"#cccccc", textSub:"#777777",
  gold:"#c8a96e", goldDim:"#c8a96e22",
  mono:"'DM Mono',monospace", serif:"'Lora',serif",
};

interface Dormain { id:string; name:string; }
interface Score { dormain_id:string; score:number; peak_score:number; }
interface WHClaim { id:string; dormain_id:string; status:string; value_wh:number; credential_type:string; }

export default function CompetencePage() {
  const [dormains, setDormains] = useState<Dormain[]>([]);
  const [scores,   setScores]   = useState<Score[]>([]);
  const [claims,   setClaims]   = useState<WHClaim[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [showClaim,setShowClaim]= useState(false);
  const [claimForm,setClaimForm]= useState({ dormain_id:"", credential_type:"degree", value_wh:1000, value_claimed:"", vdc_reference:"" });
  const [posting,  setPosting]  = useState(false);

  useEffect(()=>{
    Promise.allSettled([
      competenceApi.dormains(),
      competenceApi.scores(),
      competenceApi.whClaims(),
    ]).then(([dr,sr,wr])=>{
      if (dr.status==="fulfilled") setDormains(dr.value.data ?? []);
      if (sr.status==="fulfilled") setScores(sr.value.data?.items ?? sr.value.data ?? []);
      if (wr.status==="fulfilled") setClaims(wr.value.data?.items ?? wr.value.data ?? []);
    }).finally(()=>setLoading(false));
  },[]);

  async function submitClaim() {
    if (!claimForm.dormain_id || !claimForm.value_claimed) return;
    setPosting(true);
    try {
      await competenceApi.submitWh(claimForm);
      setShowClaim(false);
      const wr = await competenceApi.whClaims();
      setClaims(wr.data?.items ?? wr.data ?? []);
    } finally { setPosting(false); }
  }

  const scoreMap = Object.fromEntries(scores.map(s=>[s.dormain_id,s]));
  const dormainName = (id:string) => dormains.find(d=>d.id===id)?.name ?? id.slice(0,8);
  const claimStatus: Record<string,string> = { pending:T.gold, enacted:"#5a8a6a", rejected:"#c87a6e" };

  const maxScore = Math.max(...scores.map(s=>s.score), 1);

  return (
    <div style={{ maxWidth:680 }}>

      {/* W_s scores */}
      <div style={{ marginBottom:28 }}>
        <p style={{ margin:"0 0 12px", fontSize:9, color:T.muted,
          letterSpacing:2, textTransform:"uppercase" }}>Soft Competence (W_s)</p>
        {loading
          ? <p style={{ color:T.muted, fontSize:10 }}>Loading…</p>
          : dormains.length===0
          ? <p style={{ color:T.muted, fontSize:10 }}>No dormains defined.</p>
          : (
          <div style={{ border:`1px solid ${T.border}`, borderRadius:6,
            background:T.surface, overflow:"hidden" }}>
            {dormains.map((d,i)=>{
              const sc = scoreMap[d.id];
              const val = sc?.score ?? 0;
              const pct = Math.round((val/maxScore)*100);
              return (
                <div key={d.id} style={{
                  padding:"10px 14px",
                  borderBottom:i<dormains.length-1?`1px solid ${T.border}`:"none",
                }}>
                  <div style={{ display:"flex", justifyContent:"space-between",
                    marginBottom:5 }}>
                    <span style={{ fontSize:11, color:T.text,
                      fontFamily:T.serif }}>{d.name}</span>
                    <span style={{ fontSize:12, color:T.gold,
                      fontFamily:T.mono }}>{Math.round(val)}</span>
                  </div>
                  <div style={{ height:2, background:T.dim, borderRadius:1 }}>
                    <div style={{ height:"100%", borderRadius:1,
                      background:T.gold, width:`${pct}%`,
                      transition:"width 0.4s ease" }}/>
                  </div>
                  {sc && (
                    <p style={{ margin:"4px 0 0", fontSize:8, color:T.muted }}>
                      peak {Math.round(sc.peak_score)}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* W_h claims */}
      <div>
        <div style={{ display:"flex", justifyContent:"space-between",
          alignItems:"center", marginBottom:12 }}>
          <p style={{ margin:0, fontSize:9, color:T.muted,
            letterSpacing:2, textTransform:"uppercase" }}>Hard Competence (W_h) Claims</p>
          <button onClick={()=>setShowClaim(c=>!c)} style={{
            padding:"4px 10px", background:showClaim?T.goldDim:"transparent",
            border:`1px solid ${showClaim?T.gold:T.dim}`, borderRadius:4,
            cursor:"pointer", fontFamily:T.mono, fontSize:9,
            color:showClaim?T.gold:T.muted, letterSpacing:1,
          }}>{showClaim?"✕ cancel":"+ submit claim"}</button>
        </div>

        {showClaim && (
          <div style={{ padding:"14px", border:`1px solid ${T.border}`,
            borderRadius:6, background:T.raised, marginBottom:14 }}>
            <div style={{ display:"grid", gap:10, marginBottom:12 }}>
              {[
                { label:"Dormain", el:(
                  <select value={claimForm.dormain_id}
                    onChange={e=>setClaimForm(p=>({...p,dormain_id:e.target.value}))}
                    style={{ width:"100%", background:T.raised, border:`1px solid ${T.border}`,
                      color:T.text, fontFamily:T.mono, fontSize:10, padding:"6px 8px",
                      borderRadius:4, outline:"none" }}>
                    <option value="">Select dormain…</option>
                    {dormains.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                )},
                { label:"Type", el:(
                  <select value={claimForm.credential_type}
                    onChange={e=>setClaimForm(p=>({...p,credential_type:e.target.value}))}
                    style={{ width:"100%", background:T.raised, border:`1px solid ${T.border}`,
                      color:T.text, fontFamily:T.mono, fontSize:10, padding:"6px 8px",
                      borderRadius:4, outline:"none" }}>
                    {["degree","certification","patent","license","verified_contribution"].map(t=>(
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                )},
                { label:"Claim (e.g. PhD in CS, MIT 2018)", el:(
                  <input value={claimForm.value_claimed}
                    onChange={e=>setClaimForm(p=>({...p,value_claimed:e.target.value}))}
                    placeholder="Describe the credential…"
                    style={{ width:"100%", background:T.raised, border:`1px solid ${T.border}`,
                      color:T.text, fontFamily:T.mono, fontSize:10, padding:"6px 8px",
                      borderRadius:4, outline:"none" }}/>
                )},
                { label:"Reference URL / VDC (optional)", el:(
                  <input value={claimForm.vdc_reference}
                    onChange={e=>setClaimForm(p=>({...p,vdc_reference:e.target.value}))}
                    placeholder="https://…"
                    style={{ width:"100%", background:T.raised, border:`1px solid ${T.border}`,
                      color:T.text, fontFamily:T.mono, fontSize:10, padding:"6px 8px",
                      borderRadius:4, outline:"none" }}/>
                )},
              ].map(({label,el})=>(
                <div key={label}>
                  <p style={{ margin:"0 0 4px", fontSize:8, color:T.muted,
                    letterSpacing:1, textTransform:"uppercase" }}>{label}</p>
                  {el}
                </div>
              ))}
            </div>
            <div style={{ display:"flex", justifyContent:"flex-end" }}>
              <button onClick={submitClaim}
                disabled={posting||!claimForm.dormain_id||!claimForm.value_claimed}
                style={{ padding:"5px 14px", background:T.goldDim,
                  border:`1px solid ${T.gold}50`, borderRadius:4,
                  color:T.gold, fontFamily:T.mono, fontSize:9, cursor:"pointer",
                  letterSpacing:1, opacity:posting?0.4:1 }}>
                {posting?"submitting…":"submit claim →"}
              </button>
            </div>
          </div>
        )}

        {claims.length===0
          ? <p style={{ color:T.muted, fontSize:10 }}>No W_h claims yet.</p>
          : (
          <div style={{ border:`1px solid ${T.border}`, borderRadius:6,
            background:T.surface, overflow:"hidden" }}>
            {claims.map((c,i)=>(
              <div key={c.id} style={{ padding:"10px 14px",
                borderBottom:i<claims.length-1?`1px solid ${T.border}`:"none" }}>
                <div style={{ display:"flex", justifyContent:"space-between",
                  marginBottom:3 }}>
                  <span style={{ fontSize:11, color:T.text, fontFamily:T.serif }}>
                    {dormainName(c.dormain_id)}
                  </span>
                  <span style={{ fontSize:9, fontFamily:T.mono,
                    color:claimStatus[c.status]??T.muted }}>{c.status}</span>
                </div>
                <div style={{ display:"flex", gap:12 }}>
                  <span style={{ fontSize:9, color:T.textSub }}>{c.credential_type}</span>
                  <span style={{ fontSize:9, color:T.gold, fontFamily:T.mono }}>
                    W_h {c.value_wh}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
