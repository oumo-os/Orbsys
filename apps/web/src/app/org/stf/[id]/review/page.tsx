"use client";
// Unified Blind Review page — handles both motion aSTF (4-dim rubric)
// and periodic aSTF (circle rubric + per-assigned-member rubric)
// See apps/api/src/bootstrap/rubrics.py for dimension definitions.
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth";

function DimensionSlider({ dim, value, onChange }: {
  dim: { key: string; label: string; max: number; description: string };
  value: number; onChange: (v: number) => void;
}) {
  const pct = dim.max > 0 ? Math.round((value / dim.max) * 100) : 0;
  const c = pct >= 75 ? "var(--green,#5a9e6e)" : pct >= 40 ? "var(--gold)" : "var(--red,#c0392b)";
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ display:"flex", justifyContent:"space-between", marginBottom: 5 }}>
        <span style={{ fontSize:12, color:"var(--text)", fontFamily:"var(--font-display,'Lora',serif)" }}>{dim.label}</span>
        <span style={{ fontSize:12, fontFamily:"monospace", color:c }}>{value} / {dim.max}</span>
      </div>
      <input type="range" min={0} max={dim.max} step={1} value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{ width:"100%", accentColor:c, cursor:"pointer" }} />
      <p style={{ margin:"4px 0 0", fontSize:10, color:"var(--text-dim)",
        fontFamily:"var(--font-display,'Lora',serif)", lineHeight:1.5 }}>{dim.description}</p>
    </div>
  );
}

function MemberPanel({ member, memberDimensions, memberFlags, scores, note, onChange, onNoteChange }: {
  member: Record<string,unknown>;
  memberDimensions: { key:string; label:string; max:number; description:string }[];
  memberFlags: { key:string; label:string; max:number; description:string; flag_threshold:number }[];
  scores: Record<string,number>; note: string;
  onChange: (k:string, v:number) => void; onNoteChange: (v:string) => void;
}) {
  const [open, setOpen] = useState(true);
  const healthTotal = memberDimensions.reduce((s,d) => s+(scores[d.key]??0), 0);
  const maxHealth   = memberDimensions.reduce((s,d) => s+d.max, 0);
  const pct = maxHealth ? Math.round((healthTotal/maxHealth)*100) : 0;
  const c = pct>=75?"var(--green,#5a9e6e)":pct>=40?"var(--gold)":"var(--red,#c0392b)";
  return (
    <div style={{ border:"1px solid var(--border)", borderRadius:9, marginBottom:12, overflow:"hidden" }}>
      <button onClick={() => setOpen(o=>!o)} style={{
        width:"100%", padding:"12px 16px", background:"var(--surface-raised)", border:"none",
        display:"flex", justifyContent:"space-between", alignItems:"center", cursor:"pointer" }}>
        <span style={{ fontFamily:"var(--font-display,'Lora',serif)", fontSize:13, color:"var(--text)" }}>
          @{String(member.handle)}
        </span>
        <div style={{ display:"flex", gap:12, alignItems:"center" }}>
          <span style={{ fontFamily:"monospace", fontSize:11, color:c }}>{healthTotal}/{maxHealth}</span>
          <span style={{ fontSize:10, color:"var(--text-dim)" }}>{open?"▲":"▼"}</span>
        </div>
      </button>
      {open && (
        <div style={{ padding:"16px 20px" }}>
          <div style={{ display:"flex", gap:16, flexWrap:"wrap", marginBottom:16,
            padding:"10px 14px", background:"var(--surface)", borderRadius:7,
            border:"1px solid var(--border)" }}>
            {([
              ["W_s", String(member.primary_dormain_ws??"—")],
              ["Contributions 90d", String(member.contributions_90d??"—")],
              ["Votes 90d", String(member.votes_90d??"—")],
              ["Verdicts 90d", String(member.verdicts_90d??"—")],
              ["Posts 90d", String(member.posts_90d??"—")],
            ] as [string, string][]).map(([label,val]) => (
              <div key={String(label)}>
                <p style={{ margin:"0 0 2px", fontSize:9, color:"var(--text-dim)",
                  fontFamily:"monospace", textTransform:"uppercase" }}>{label}</p>
                <p style={{ margin:0, fontSize:15, fontFamily:"monospace", color:"var(--text)" }}>{String(val)}</p>
              </div>
            ))}
          </div>
          {memberDimensions.map(dim => (
            <DimensionSlider key={dim.key} dim={dim} value={scores[dim.key]??0}
              onChange={v => onChange(dim.key, v)} />
          ))}
          <div style={{ marginTop:8, paddingTop:12, borderTop:"1px solid var(--border)" }}>
            <p style={{ margin:"0 0 10px", fontSize:10, color:"var(--text-muted)",
              fontFamily:"monospace", textTransform:"uppercase", letterSpacing:1 }}>
              Risk signals (not added to health score)
            </p>
            {memberFlags.map(flag => (
              <DimensionSlider key={flag.key} dim={flag} value={scores[flag.key]??0}
                onChange={v => onChange(flag.key, v)} />
            ))}
          </div>
          <textarea value={note} onChange={e => onNoteChange(e.target.value)}
            placeholder="Optional note (part of sealed record)" rows={2}
            style={{ width:"100%", boxSizing:"border-box", marginTop:10, padding:"8px 12px",
              background:"var(--surface-raised)", border:"1px solid var(--border)",
              borderRadius:7, color:"var(--text)", fontFamily:"var(--font-display,'Lora',serif)",
              fontSize:12, resize:"vertical", outline:"none" }} />
        </div>
      )}
    </div>
  );
}

export default function BlindReviewPage() {
  const params = useParams();
  const router = useRouter();
  const stfId  = params.id as string;
  const isolatedToken = useAuthStore((s) => s.isolatedToken);
  const blindApiUrl   = process.env.NEXT_PUBLIC_BLIND_API_URL ?? "http://localhost:8001";

  const [content,    setContent]    = useState<Record<string,unknown>|null>(null);
  const [loading,    setLoading]    = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted,  setSubmitted]  = useState(false);
  const [error,      setError]      = useState<string|null>(null);

  const [motionDimScores,  setMotionDimScores]  = useState<Record<string,number>>({});
  const [verdict,          setVerdict]          = useState("");
  const [rationale,        setRationale]        = useState("");
  const [revisionDirective,setRevisionDirective]= useState("");

  const [circleScores,    setCircleScores]    = useState<Record<string,number>>({});
  const [memberScoresMap, setMemberScoresMap] = useState<Record<string,Record<string,number>>>({});
  const [memberNotesMap,  setMemberNotesMap]  = useState<Record<string,string>>({});

  useEffect(() => {
    if (!isolatedToken) return;
    fetch(`${blindApiUrl}/blind/${stfId}/content`, {
      headers: { "X-Isolated-View-Token": isolatedToken },
    })
      .then(r => r.json())
      .then(data => {
        setContent(data);
        const rubric  = (data.rubric as Record<string,unknown>) ?? {};
        const mDims   = (rubric.dimensions as {key:string}[]) ?? [];
        const cDims   = (rubric.circle_dimensions as {key:string}[]) ?? [];
        const memDims = [...(rubric.member_dimensions as {key:string}[] ?? []),
                         ...(rubric.member_flags      as {key:string}[] ?? [])];
        setMotionDimScores(Object.fromEntries(mDims.map(d=>[d.key,0])));
        setCircleScores(Object.fromEntries(cDims.map(d=>[d.key,0])));
        const members = (data.assigned_members as {member_id:string}[]) ?? [];
        setMemberScoresMap(Object.fromEntries(
          members.map(m => [m.member_id, Object.fromEntries(memDims.map(d=>[d.key,0]))])
        ));
      })
      .catch(() => setError("Could not load review content."))
      .finally(() => setLoading(false));
  }, [stfId, isolatedToken, blindApiUrl]);

  async function submit() {
    if (!isolatedToken || !verdict || !rationale) return;
    setSubmitting(true); setError(null);
    const rubricType = (content?.rubric_type as string) ?? "motion_astf";
    const body: Record<string,unknown> = { verdict, rationale };
    if (rubricType === "periodic_astf") {
      body.circle_scores = circleScores;
      body.health_tier   = verdict;
      const rubric   = (content?.rubric as Record<string,unknown>) ?? {};
      const memDims  = (rubric.member_dimensions as {key:string}[]) ?? [];
      const memFlags = (rubric.member_flags      as {key:string}[]) ?? [];
      const allKeys  = [...memDims.map(d=>d.key), ...memFlags.map(d=>d.key)];
      body.member_scores = ((content?.assigned_members as {member_id:string}[]) ?? []).map(m => ({
        member_id: m.member_id,
        note: memberNotesMap[m.member_id] ?? "",
        ...Object.fromEntries(allKeys.map(k => [k, (memberScoresMap[m.member_id]??{})[k]??0])),
      }));
    } else {
      body.dimension_scores = motionDimScores;
      if (revisionDirective) body.revision_directive = revisionDirective;
    }
    try {
      const r = await fetch(`${blindApiUrl}/blind/${stfId}/verdicts`, {
        method:"POST", headers:{ "Content-Type":"application/json",
          "X-Isolated-View-Token":isolatedToken }, body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? "Submission failed");
      setSubmitted(true);
      setTimeout(() => router.push(`/org/stf/${stfId}`), 2000);
    } catch(e) { setError(String((e as Error).message)); }
    finally { setSubmitting(false); }
  }

  if (!isolatedToken) return <div style={{ padding:48, fontFamily:"monospace", fontSize:12, color:"var(--text-muted)" }}>No isolated view token.</div>;
  if (loading)   return <div style={{ padding:48, fontFamily:"monospace", fontSize:12, color:"var(--text-muted)" }}>Loading…</div>;
  if (submitted) return <div style={{ padding:48, textAlign:"center" }}><p style={{ fontSize:16, color:"var(--green,#5a9e6e)", fontFamily:"var(--font-display,'Lora',serif)" }}>Verdict filed. Returning…</p></div>;
  if (!content)  return <div style={{ padding:48, fontFamily:"monospace", fontSize:11, color:"var(--red,#c0392b)" }}>{error ?? "Content not available."}</div>;

  const rubricType  = (content.rubric_type as string) ?? "motion_astf";
  const rubric      = (content.rubric as Record<string,unknown>) ?? {};
  const isPASTF     = rubricType === "periodic_astf";
  const motionDims  = (rubric.dimensions         as {key:string;label:string;max:number;description:string}[]) ?? [];
  const circleDims  = (rubric.circle_dimensions  as {key:string;label:string;max:number;description:string}[]) ?? [];
  const memberDims  = (rubric.member_dimensions  as {key:string;label:string;max:number;description:string}[]) ?? [];
  const memberFlags = (rubric.member_flags       as {key:string;label:string;max:number;description:string;flag_threshold:number}[]) ?? [];
  const assigned    = (content.assigned_members  as Record<string,unknown>[]) ?? [];
  const circleInfo  = content.circle as Record<string,unknown>;
  const motionTotal = (rubric.total as number)         ?? 30;
  const circleTotal = (rubric.circle_total as number)  ?? 30;
  const motionScore = Object.values(motionDimScores).reduce((s,v)=>s+v,0);
  const circleScore = Object.values(circleScores).reduce((s,v)=>s+v,0);
  const verdictOpts = isPASTF ? ["healthy","watch","concern"] : ["approve","revision_request","reject"];

  return (
    <div style={{ maxWidth:700, margin:"0 auto", padding:"32px 20px" }}>
      <div style={{ marginBottom:32 }}>
        <p style={{ margin:"0 0 6px", fontSize:10, color:"var(--gold)", fontFamily:"monospace",
          letterSpacing:3, textTransform:"uppercase" }}>
          {isPASTF ? "Periodic Audit Review" : "Motion Audit Review"} · Sealed
        </p>
        <h1 style={{ margin:"0 0 8px", fontSize:22,
          fontFamily:"var(--font-display,'Lora',serif)", fontWeight:400 }}>
          {isPASTF && circleInfo ? `${String(circleInfo.name)} — Circle Health Review`
            : String(content.mandate ?? "").slice(0,80)}
        </h1>
        <p style={{ margin:0, fontSize:11, color:"var(--text-muted)", fontFamily:"monospace" }}>
          Your identity is permanently sealed. Scores and verdicts go to the open ledger.
        </p>
      </div>

      {isPASTF && circleInfo && (
        <div style={{ padding:"16px 20px", background:"var(--surface)",
          border:"1px solid var(--border)", borderRadius:10, marginBottom:28 }}>
          <p style={{ margin:"0 0 12px", fontSize:10, color:"var(--text-muted)",
            fontFamily:"monospace", textTransform:"uppercase", letterSpacing:1 }}>Circle public profile</p>
          <div style={{ display:"flex", gap:20, flexWrap:"wrap" }}>
            {([
              ["Members",String(circleInfo.member_count)],
              ["Competence fit",`${circleInfo.competence_fit_pct}%`],
              ["Motions 90d",String(circleInfo.motions_filed_90d)],
              ["Enacted 90d",String(circleInfo.resolutions_enacted_90d)],
            ] as [string, string][]).map(([l,v]) => (
              <div key={String(l)}>
                <p style={{ margin:"0 0 2px", fontSize:9, color:"var(--text-dim)",
                  fontFamily:"monospace", textTransform:"uppercase" }}>{l}</p>
                <p style={{ margin:0, fontSize:18, fontFamily:"monospace", color:"var(--text)" }}>{String(v)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {!isPASTF && motionDims.length > 0 && (
        <div style={{ padding:"20px 24px", background:"var(--surface)",
          border:"1px solid var(--border)", borderRadius:10, marginBottom:24 }}>
          <div style={{ display:"flex", justifyContent:"space-between", marginBottom:16 }}>
            <p style={{ margin:0, fontSize:10, color:"var(--text-muted)",
              fontFamily:"monospace", textTransform:"uppercase", letterSpacing:1 }}>Audit dimensions</p>
            <p style={{ margin:0, fontSize:13, fontFamily:"monospace",
              color:motionScore>=motionTotal*0.75?"var(--green,#5a9e6e)":motionScore>=motionTotal*0.5?"var(--gold)":"var(--red,#c0392b)" }}>
              {motionScore} / {motionTotal}
            </p>
          </div>
          {motionDims.map(dim => (
            <DimensionSlider key={dim.key} dim={dim} value={motionDimScores[dim.key]??0}
              onChange={v => setMotionDimScores(p=>({...p,[dim.key]:v}))} />
          ))}
        </div>
      )}

      {isPASTF && circleDims.length > 0 && (
        <div style={{ padding:"20px 24px", background:"var(--surface)",
          border:"1px solid var(--border)", borderRadius:10, marginBottom:24 }}>
          <div style={{ display:"flex", justifyContent:"space-between", marginBottom:16 }}>
            <p style={{ margin:0, fontSize:10, color:"var(--text-muted)",
              fontFamily:"monospace", textTransform:"uppercase", letterSpacing:1 }}>Circle rubric</p>
            <p style={{ margin:0, fontSize:13, fontFamily:"monospace", color:"var(--gold)" }}>
              {circleScore} / {circleTotal}
            </p>
          </div>
          {circleDims.map(dim => (
            <DimensionSlider key={dim.key} dim={dim} value={circleScores[dim.key]??0}
              onChange={v => setCircleScores(p=>({...p,[dim.key]:v}))} />
          ))}
        </div>
      )}

      {isPASTF && assigned.length > 0 && (
        <div style={{ marginBottom:24 }}>
          <p style={{ margin:"0 0 12px", fontSize:10, color:"var(--text-muted)",
            fontFamily:"monospace", textTransform:"uppercase", letterSpacing:1 }}>
            Assigned members ({assigned.length})
          </p>
          {assigned.map(m => {
            const mid = String(m.member_id);
            const all = memberScoresMap[mid] ?? {};
            return (
              <MemberPanel key={mid} member={m} memberDimensions={memberDims} memberFlags={memberFlags}
                scores={all} note={memberNotesMap[mid]??""} onChange={(k,v) => setMemberScoresMap(p=>({
                  ...p, [mid]:{...(p[mid]??{}),[k]:v}
                }))} onNoteChange={n => setMemberNotesMap(p=>({...p,[mid]:n}))} />
            );
          })}
        </div>
      )}

      <div style={{ padding:"20px 24px", background:"var(--surface)",
        border:"1px solid var(--border)", borderRadius:10, marginBottom:20 }}>
        <p style={{ margin:"0 0 12px", fontSize:10, color:"var(--text-muted)",
          fontFamily:"monospace", textTransform:"uppercase", letterSpacing:1 }}>
          {isPASTF ? "Health tier" : "Verdict"}
        </p>
        <div style={{ display:"flex", gap:8, marginBottom:16 }}>
          {verdictOpts.map(v => (
            <button key={v} onClick={() => setVerdict(v)} style={{
              flex:1, padding:"10px",
              background:verdict===v?"var(--gold-glow)":"transparent",
              border:`1px solid ${verdict===v?"var(--gold)":"var(--border)"}`,
              borderRadius:7, color:verdict===v?"var(--gold)":"var(--text-muted)",
              fontFamily:"monospace", fontSize:11, cursor:"pointer",
              textTransform:"uppercase", letterSpacing:0.5 }}>
              {v.replace("_"," ")}
            </button>
          ))}
        </div>
        <textarea value={rationale} onChange={e=>setRationale(e.target.value)}
          placeholder="Required: brief rationale. Published to ledger."
          rows={4} style={{ width:"100%", boxSizing:"border-box", padding:"10px 14px",
            background:"var(--surface-raised)", border:"1px solid var(--border)",
            borderRadius:8, color:"var(--text)", fontFamily:"var(--font-display,'Lora',serif)",
            fontSize:13, resize:"vertical", outline:"none", lineHeight:1.65 }} />
        {!isPASTF && verdict==="revision_request" && (
          <textarea value={revisionDirective} onChange={e=>setRevisionDirective(e.target.value)}
            placeholder="Revision directive (required for revision request)"
            rows={3} style={{ width:"100%", boxSizing:"border-box", marginTop:10, padding:"10px 14px",
              background:"var(--surface-raised)", border:"1px solid var(--gold)",
              borderRadius:8, color:"var(--text)", fontFamily:"var(--font-display,'Lora',serif)",
              fontSize:12, resize:"vertical", outline:"none" }} />
        )}
      </div>

      {error && <p style={{ margin:"0 0 12px", fontSize:11, color:"var(--red,#c0392b)", fontFamily:"monospace" }}>{error}</p>}

      <button onClick={submit} disabled={submitting||!verdict||!rationale} style={{
        width:"100%", padding:"14px", background:"var(--gold-glow)",
        border:"1px solid var(--gold)", borderRadius:9, color:"var(--gold)",
        fontFamily:"monospace", fontSize:12, cursor:"pointer", letterSpacing:1,
        textTransform:"uppercase", opacity:(submitting||!verdict||!rationale)?0.45:1 }}>
        {submitting?"Filing verdict…":"File verdict →"}
      </button>
      <p style={{ marginTop:12, fontSize:10, textAlign:"center", color:"var(--text-dim)", fontFamily:"monospace" }}>
        Once filed, this verdict cannot be modified. Reviewer identity is permanently sealed.
      </p>
    </div>
  );
}
