import { useState } from "react";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, BarChart, Bar, XAxis, Tooltip } from "recharts";

const T = {
  bg:"#050505",surface:"#080808",panel:"#0b0b0b",border:"#141414",border2:"#1e1e1e",
  gold:"#c8a96e",goldDim:"#c8a96e40",green:"#6ea880",blue:"#6e8dc8",red:"#c87a6e",
  muted:"#3a3a3a",dim:"#252525",text:"#cccccc",textSub:"#888888",textDim:"#555555",
  mono:"'DM Mono', monospace",serif:"'Lora', serif",
};

const ME = {
  name:"Amara Osei",handle:"amara.osei",joined:"March 2023",
  bio:"Governance researcher & protocol contributor. Interested in anti-fragile collective systems and participatory design.",
  competences:[
    {domain:"Protocol Eng.",Wh:1840,Ws:1690,Weff:1780},
    {domain:"UX Design",Wh:1920,Ws:1780,Weff:1870},
    {domain:"Community",Wh:1650,Ws:1820,Weff:1720},
    {domain:"Security",Wh:1780,Ws:1540,Weff:1680},
    {domain:"Research",Wh:1510,Ws:1620,Weff:1560},
  ],
  curiosities:[
    {tag:"zero-knowledge-proofs",w:0.91},{tag:"participatory-design",w:0.85},
    {tag:"anti-fragile-systems",w:0.78},{tag:"deliberative-democracy",w:0.72},
    {tag:"collective-intelligence",w:0.68},{tag:"distributed-identity",w:0.55},
  ],
  circles:["Protocol Engineering","User Experience"],
  stfs:["aSTF-12 · Research Collective"],
  history:{motionsInfluenced:14,resolutions:9,cellsInitiated:7,proposalsSponsored:3,commonsThreads:42},
};

const ORG = {
  name:"Orbis Collective",
  mandate:"A fluid, non-territorial research and protocol collective. Founded on the principle that legitimate authority is earned, audited, and continuously renewed.",
  domains:[
    {name:"Protocol Eng.",activity:87},{name:"Treasury",activity:64},{name:"Community",activity:91},
    {name:"Security",activity:73},{name:"UX Design",activity:78},{name:"Research",activity:59},
  ],
  circles:[
    {name:"Protocol Engineering",members:8,auditHealth:94,motions:3},
    {name:"Treasury Management",members:5,auditHealth:88,motions:1},
    {name:"Community Relations",members:7,auditHealth:97,motions:2},
    {name:"Security Assurance",members:5,auditHealth:91,motions:0},
    {name:"User Experience",members:6,auditHealth:99,motions:2},
    {name:"Research Collective",members:5,auditHealth:85,motions:1},
  ],
  activeMotions:[
    {title:"Dynamic Quorum Thresholds v2",circle:"Protocol Engineering",status:"deliberating",date:"Feb 22"},
    {title:"Onboarding Pathway Redesign",circle:"Community Relations",status:"drafting",date:"Feb 20"},
    {title:"Burnout Guardrail Parameters",circle:"User Experience",status:"finalising",date:"Feb 15"},
    {title:"Emergency Pause Mechanism",circle:"Protocol Engineering",status:"deliberating",date:"Feb 24"},
  ],
  resolutions:[
    {id:"RES-041",title:"Dual Competence Metric v2 — Parameter Revision",circle:"Protocol Engineering",adopted:"Jan 14, 2026",summary:"Revises Wh/Ws weighting formula. Sets K-factor floors at 1200 rating. Supersedes RES-038.",references:["RES-038","RES-029"],immutable:true},
    {id:"RES-040",title:"STF Rotation Schedule — 2–12 Week Mandate Cap",circle:"Community Relations",adopted:"Dec 28, 2025",summary:"Establishes mandatory rotation bounds. No STF mandate may exceed 12 weeks. All mandates must include quorum of 3+ members.",references:["RES-033"],immutable:true},
    {id:"RES-039",title:"Q1 Treasury Reallocation — Research Domain",circle:"Treasury Management",adopted:"Feb 18, 2026",summary:"Reallocates 18% of discretionary reserves to Research Collective domain fund for H1 2026.",references:["RES-031","RES-036"],immutable:true},
    {id:"RES-038",title:"Domain Weight Normalisation Protocol",circle:"Protocol Engineering",adopted:"Nov 3, 2025",summary:"Establishes that all post domain weights normalise to 1.0. Primary domain receives full Ws effect; others scale relatively.",references:[],immutable:true},
    {id:"RES-037",title:"Cell Commissioning Authority — Circle Rights",circle:"Community Relations",adopted:"Oct 11, 2025",summary:"Circles hold authority to create, close, or restrict any Cell within their mandate domain. STF cells expire with mandate.",references:["RES-030"],immutable:true},
  ],
  health:{autonomy:87,auditCoverage:94,stfRotation:72,participation:81},
  curiosities:[{tag:"distributed-identity",w:0.88},{tag:"anti-fragile-systems",w:0.82},{tag:"zk-proofs",w:0.76}],
};

const CIRCLE = {
  name:"Protocol Engineering",
  mandate:"Responsible for all decisions affecting the core protocol layer, consensus mechanisms, and governance parameter changes.",
  members:8,domains:["protocol-engineering","security-assurance","research"],
  mandateDomains:["protocol-engineering","security-assurance","research"],
  domainActivity:[
    {name:"protocol-eng.",activity:84,mandate:true},
    {name:"security",activity:61,mandate:true},
    {name:"research",activity:43,mandate:true},
    {name:"community",activity:18,mandate:false},
    {name:"ux-design",activity:11,mandate:false},
  ],
  cells:[
    {title:"Dynamic Quorum Thresholds v2",status:"deliberating",participants:6,age:"2d"},
    {title:"Weighted Vote Decay Proposal",status:"drafting",participants:4,age:"5d"},
    {title:"Emergency Pause Mechanism Review",status:"finalising",participants:8,age:"8d"},
  ],
  stfCells:[
    {title:"aSTF-09 · Protocol Q1 Audit",status:"active",deadline:"Mar 10",progress:62},
    {title:"xSTF · Consensus Mechanism Study",status:"concluded",deadline:"Feb 12",progress:100},
  ],
  feed:[
    {author:"Kofi Mensah",action:"posted in",cell:"Dynamic Quorum Thresholds v2",domain:"protocol-engineering",w:0.7,time:"12m"},
    {author:"aSTF-09",action:"flagged",cell:"Q1 Audit · parameter anomaly",domain:"security-assurance",w:null,time:"1h"},
    {author:"Inferential Eng",action:"matched to",cell:"Weighted Vote Decay Proposal",domain:"research",w:null,time:"2h"},
    {author:"Priya Nair",action:"sponsored →",cell:"Emergency Pause Mechanism Review",domain:"security-assurance",w:0.4,time:"4h"},
  ],
};

const STF = {
  name:"aSTF-12",type:"Audit Short-Term Facilitator",circle:"Research Collective",
  mandate:"Independent audit of the Research Collective's Q4 2024 activities, domain weight calibration, and Ws accrual validity.",
  members:["Amara Osei","Dayo Adeyemi","Selin Çelik"],
  commissioned:"Jan 28, 2026",deadline:"Mar 15, 2026",progress:41,daysLeft:17,daysTotal:46,
  parentCell:"Research Collective · Q4 Audit Commission",
  metrics:[
    {label:"Posts reviewed",value:"84 / 210",pct:40},
    {label:"Ws anomalies flagged",value:"3",pct:null},
    {label:"Domain calibrations",value:"2 pending",pct:null},
    {label:"Quorum status",value:"3/3 active",pct:null},
  ],
  log:[
    {entry:"Reviewed posts 001–084. Two Ws inflation patterns identified in sociology domain.",date:"Feb 24"},
    {entry:"Cross-referenced domain weights against Integrity Engine baseline. One calibration filed.",date:"Feb 20"},
    {entry:"aSTF-12 constituted. Mandate and scope confirmed with commissioning circle.",date:"Jan 28"},
  ],
};

const COMMONS_FEED = [
  {id:"p1",author:"Nneka Obi",time:"4m ago",body:"Has anyone looked at how our domain weight assignments handle cross-disciplinary posts? The sociology weight on last month's HQ thread felt underweighted given the content.",domains:[{d:"sociology",w:0.51},{d:"governance",w:0.29},{d:"community",w:0.20}],replies:7,relays:3,sponsored:false},
  {id:"p2",author:"Kofi Mensah",time:"31m ago",body:"Sharing initial findings from the consensus mechanism review. K-factor volatility at low rating bands appears to be compressing participation from new contributors.",domains:[{d:"protocol-engineering",w:0.68},{d:"research",w:0.22},{d:"community",w:0.10}],replies:12,relays:8,sponsored:true,sponsoredBy:"Priya Nair · Protocol Engineering"},
  {id:"p3",author:"Selin Çelik",time:"1h ago",body:"Curious whether the proposed HQ governance structure should inherit org-level credibility rules or start fresh. The case for fresh start aligns with the non-transfer principle between domains.",domains:[{d:"governance",w:0.44},{d:"community",w:0.33},{d:"research",w:0.23}],replies:5,relays:2,sponsored:false},
  {id:"p4",author:"Yusuf Balogun",time:"2h ago",body:"The Insight Engine summary of last week's onboarding thread is live. Highlights the tension between curiosity-led matching and minimum competence floors for STF eligibility.",domains:[{d:"community",w:0.55},{d:"protocol-engineering",w:0.25},{d:"ux-design",w:0.20}],replies:9,relays:11,sponsored:false},
];

const OPEN_CELLS = [
  {title:"HQ Governance Architecture Discussion",author:"Amara Osei",participants:19,age:"3d",curiosityMatch:88},
  {title:"Notification Frequency — UX Research",author:"Priya Nair",participants:11,age:"1d",curiosityMatch:82},
  {title:"Integrity Engine Transparency Audit",author:"Kofi Mensah",participants:7,age:"6d",curiosityMatch:67},
];

// atoms
const Pill=({children,color=T.muted,bg="#111"})=><span style={{display:"inline-flex",alignItems:"center",gap:4,padding:"2px 9px",borderRadius:20,background:bg,color,fontSize:10,fontFamily:T.mono,letterSpacing:0.4,whiteSpace:"nowrap"}}>{children}</span>;
const Dot=({color})=><span style={{width:5,height:5,borderRadius:"50%",background:color,display:"inline-block",flexShrink:0}}/>;
const BarMini=({pct,color=T.gold})=><div style={{flex:1,height:2,background:T.border,borderRadius:1}}><div style={{width:`${pct}%`,height:"100%",background:color,borderRadius:1,transition:"width 1.2s ease"}}/></div>;

const StatusPill=({status})=>{
  const m={deliberating:["Deliberating","#1a2a1a","#6ea880","#4ea860"],drafting:["Drafting","#1a1f2a","#6e8dc8","#4e70c8"],finalising:["Finalising","#2a231a","#c8a96e","#c89040"],resolved:["Resolved","#1a1a1a","#555","#444"],active:["Active","#1a2a1a","#6ea880","#4ea860"],concluded:["Concluded","#1a1a1a","#555","#444"]};
  const [label,bg,color,dot]=m[status]||m.drafting;
  return <span style={{display:"inline-flex",alignItems:"center",gap:5,padding:"2px 9px",borderRadius:20,background:bg,color,fontSize:9,fontFamily:T.mono,letterSpacing:0.5}}><Dot color={dot}/>{label}</span>;
};

const SectionHead=({label,sub,action})=>(
  <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-end",marginBottom:18,paddingBottom:12,borderBottom:`1px solid ${T.border}`}}>
    <div>
      <p style={{margin:0,fontSize:9,fontFamily:T.mono,letterSpacing:2,textTransform:"uppercase",color:T.gold}}>{label}</p>
      {sub&&<p style={{margin:"4px 0 0",fontSize:11,color:T.muted,fontFamily:T.serif,fontStyle:"italic"}}>{sub}</p>}
    </div>
    {action&&<button onClick={action.fn} style={{padding:"5px 12px",border:`1px solid ${T.border2}`,borderRadius:5,background:"transparent",color:T.textDim,fontFamily:T.mono,fontSize:9,cursor:"pointer",letterSpacing:1,textTransform:"uppercase"}}>{action.label}</button>}
  </div>
);

const DomainTag=({d,w})=>{
  const alpha=Math.round((w/0.4)*60+15);
  return <span style={{display:"inline-flex",alignItems:"center",gap:4,padding:"2px 8px",borderRadius:20,background:`${T.blue}18`,border:`1px solid ${T.blue}${alpha.toString(16)}`,color:`${T.blue}cc`,fontSize:9,fontFamily:T.mono}}>{d} <span style={{color:`${T.blue}88`}}>{w.toFixed(2)}</span></span>;
};

function PostCard({post}){
  return(
    <div style={{padding:"16px",borderRadius:8,border:`1px solid ${T.border}`,background:T.surface,marginBottom:8}}
      onMouseEnter={e=>e.currentTarget.style.borderColor=T.border2}
      onMouseLeave={e=>e.currentTarget.style.borderColor=T.border}
    >
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:10}}>
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          <div style={{width:26,height:26,borderRadius:"50%",background:`${T.blue}22`,border:`1px solid ${T.blue}30`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:11,color:T.blue,flexShrink:0}}>{post.author[0]}</div>
          <span style={{fontSize:12,color:T.text,fontFamily:T.serif}}>{post.author}</span>
        </div>
        <span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>{post.time}</span>
      </div>
      <p style={{margin:"0 0 10px",fontSize:13,color:"#bbb",fontFamily:T.serif,lineHeight:1.65}}>{post.body}</p>
      <div style={{display:"flex",flexWrap:"wrap",gap:4,marginBottom:10}}>
        {post.domains.map(d=><DomainTag key={d.d} {...d}/>)}
      </div>
      {post.sponsored&&(
        <div style={{padding:"6px 10px",borderRadius:5,background:`${T.gold}10`,border:`1px solid ${T.gold}20`,marginBottom:8,display:"flex",alignItems:"center",gap:6}}>
          <span style={{color:T.gold,fontSize:10}}>◎</span>
          <span style={{fontSize:10,color:`${T.gold}aa`,fontFamily:T.serif,fontStyle:"italic"}}>Sponsored for formal deliberation · {post.sponsoredBy}</span>
        </div>
      )}
      <div style={{display:"flex",gap:16}}>
        {[["↩",post.replies],["⟳",post.relays]].map(([icon,count])=>(
          <button key={icon} style={{display:"flex",alignItems:"center",gap:4,border:"none",background:"transparent",color:T.muted,fontFamily:T.mono,fontSize:10,cursor:"pointer",padding:0}}>{icon} {count}</button>
        ))}
        <button style={{marginLeft:"auto",border:`1px solid ${T.border2}`,borderRadius:4,background:"transparent",color:T.muted,fontFamily:T.mono,fontSize:9,cursor:"pointer",padding:"3px 10px",letterSpacing:0.5}}>Sponsor →</button>
      </div>
    </div>
  );
}

function CommonsDash(){
  return(
    <div style={{display:"flex",gap:20}}>
      <div style={{flex:1,minWidth:0}}>
        <SectionHead label="Commons" sub="Open threads · signed to domains by Inferential Engine"/>
        <div style={{padding:"14px 16px",borderRadius:8,border:`1px solid ${T.border2}`,background:T.panel,marginBottom:20}}>
          <textarea placeholder="Post to the commons — the Inferential Engine will sign domain weights…" style={{width:"100%",background:"transparent",border:"none",outline:"none",color:"#888",fontFamily:T.serif,fontSize:12,resize:"none",lineHeight:1.7,boxSizing:"border-box"}} rows={2}/>
          <div style={{display:"flex",justifyContent:"flex-end",marginTop:6}}>
            <button style={{padding:"6px 16px",border:`1px solid ${T.goldDim}`,borderRadius:5,background:"transparent",color:T.gold,fontFamily:T.mono,fontSize:10,cursor:"pointer",letterSpacing:1}}>Post</button>
          </div>
        </div>
        {COMMONS_FEED.map(p=><PostCard key={p.id} post={p}/>)}
      </div>
      <div style={{width:236,flexShrink:0}}>
        <SectionHead label="Open Cells"/>
        {OPEN_CELLS.map(c=>(
          <div key={c.title} style={{padding:"12px 14px",borderRadius:7,border:`1px solid ${T.border}`,background:T.surface,marginBottom:7,cursor:"pointer"}}
            onMouseEnter={e=>e.currentTarget.style.borderColor=T.border2}
            onMouseLeave={e=>e.currentTarget.style.borderColor=T.border}
          >
            <p style={{margin:"0 0 6px",fontSize:12,color:"#bbb",fontFamily:T.serif,lineHeight:1.35}}>{c.title}</p>
            <div style={{display:"flex",justifyContent:"space-between"}}>
              <span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>{c.participants} participants · {c.age}</span>
              <span style={{fontSize:9,color:T.blue,fontFamily:T.mono}}>{c.curiosityMatch}% match</span>
            </div>
          </div>
        ))}
        <div style={{marginTop:24}}>
          <SectionHead label="Your Stream"/>
          {[["aSTF-12 deadline in 17 days",T.red],["New match: HQ Governance Cell",T.blue],["+24 Ws · Protocol Engineering",T.green]].map(([e,c],i)=>(
            <div key={i} style={{display:"flex",gap:8,alignItems:"flex-start",padding:"9px 0",borderBottom:`1px solid ${T.border}`}}>
              <Dot color={c}/><span style={{fontSize:11,color:T.textSub,fontFamily:T.serif}}>{e}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PersonalDash(){
  const radarData=ME.competences.map(c=>({domain:c.domain,Weff:c.Weff-1000,Wh:c.Wh-1000,Ws:c.Ws-1000}));
  return(
    <div style={{display:"flex",gap:20}}>
      <div style={{flex:1,minWidth:0}}>
        <div style={{padding:"20px",borderRadius:8,border:`1px solid ${T.border}`,background:T.surface,marginBottom:20}}>
          <div style={{display:"flex",gap:16,alignItems:"flex-start"}}>
            <div style={{width:52,height:52,borderRadius:"50%",background:"linear-gradient(135deg,#2a3040,#1a2030)",border:`1px solid ${T.goldDim}`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:20,color:T.gold,flexShrink:0}}>A</div>
            <div style={{flex:1}}>
              <h2 style={{margin:"0 0 4px",fontSize:18,color:T.text,fontFamily:T.serif,fontWeight:400}}>{ME.name}</h2>
              <p style={{margin:"0 0 8px",fontSize:10,color:T.muted,fontFamily:T.mono}}>@{ME.handle} · member since {ME.joined}</p>
              <p style={{margin:0,fontSize:12,color:T.textSub,fontFamily:T.serif,lineHeight:1.65}}>{ME.bio}</p>
            </div>
          </div>
          <div style={{display:"flex",flexWrap:"wrap",gap:6,marginTop:16,paddingTop:14,borderTop:`1px solid ${T.border}`}}>
            {ME.circles.map(c=><Pill key={c} color={T.gold} bg={`${T.gold}15`}>◎ {c}</Pill>)}
            {ME.stfs.map(s=><Pill key={s} color={T.blue} bg={`${T.blue}15`}>△ {s}</Pill>)}
          </div>
        </div>
        <SectionHead label="Dual Competence" sub="Wh (hard credentials) · Ws (contribution) · Weff (effective influence)"/>
        <div style={{height:260,marginBottom:16}}>
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radarData} margin={{top:10,right:30,bottom:10,left:30}}>
              <PolarGrid stroke={T.border2}/>
              <PolarAngleAxis dataKey="domain" tick={{fill:T.muted,fontSize:10,fontFamily:"DM Mono"}}/>
              <Radar name="Weff" dataKey="Weff" stroke={T.gold} fill={T.gold} fillOpacity={0.08} strokeWidth={1.5}/>
              <Radar name="Wh" dataKey="Wh" stroke={T.blue} fill={T.blue} fillOpacity={0.04} strokeWidth={1} strokeDasharray="4 2"/>
              <Radar name="Ws" dataKey="Ws" stroke={T.green} fill={T.green} fillOpacity={0.04} strokeWidth={1} strokeDasharray="2 3"/>
            </RadarChart>
          </ResponsiveContainer>
        </div>
        <div style={{display:"flex",gap:16,marginBottom:24,justifyContent:"center"}}>
          {[["Weff",T.gold],["Wh Hard",T.blue],["Ws Soft",T.green]].map(([l,c])=>(
            <div key={l} style={{display:"flex",alignItems:"center",gap:5}}>
              <div style={{width:16,height:1.5,background:c}}/><span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>{l}</span>
            </div>
          ))}
        </div>
        <SectionHead label="Curiosity Signals" sub="Self-declared · shapes matching, never vote weight"/>
        {ME.curiosities.map(c=>(
          <div key={c.tag} style={{display:"flex",alignItems:"center",gap:10,padding:"6px 0"}}>
            <span style={{fontSize:10,color:T.muted,fontFamily:T.mono,minWidth:210}}>#{c.tag}</span>
            <BarMini pct={c.w*100} color={T.blue}/>
            <span style={{fontSize:9,color:T.gold,fontFamily:T.mono,minWidth:30,textAlign:"right"}}>{Math.round(c.w*100)}%</span>
          </div>
        ))}
      </div>
      <div style={{width:236,flexShrink:0}}>
        <SectionHead label="Activity History"/>
        {Object.entries(ME.history).map(([k,v])=>(
          <div key={k} style={{display:"flex",justifyContent:"space-between",padding:"9px 0",borderBottom:`1px solid ${T.border}`}}>
            <span style={{fontSize:11,color:T.textSub,fontFamily:T.serif}}>{k.replace(/([A-Z])/g," $1").toLowerCase()}</span>
            <span style={{fontSize:13,color:T.gold,fontFamily:T.mono}}>{v}</span>
          </div>
        ))}
        <div style={{marginTop:24}}>
          <SectionHead label="Recent Activity"/>
          {[
            ["Posted in HQ Governance thread","4h ago",T.green],
            ["aSTF-12 log entry filed","1d ago",T.blue],
            ["Voted · Dynamic Quorum Thresholds","2d ago",T.gold],
            ["Sponsored → K-factor compression","4d ago",T.gold],
          ].map(([t,time,c],i)=>(
            <div key={i} style={{display:"flex",gap:8,padding:"9px 0",borderBottom:`1px solid ${T.border}`}}>
              <Dot color={c}/>
              <div><p style={{margin:"0 0 2px",fontSize:11,color:T.textSub,fontFamily:T.serif}}>{t}</p><span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>{time}</span></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ResolutionCard({res,expanded,onToggle}){
  return(
    <div style={{borderRadius:7,border:`1px solid ${expanded?"#2a2010":T.border}`,background:expanded?"#0c0a05":T.panel,marginBottom:6,overflow:"hidden",transition:"all 0.15s",cursor:"pointer"}} onClick={onToggle}>
      <div style={{padding:"13px 16px",display:"flex",alignItems:"center",gap:12}}>
        {/* immutability mark */}
        <span style={{fontFamily:T.mono,fontSize:9,color:`${T.gold}60`,letterSpacing:1,flexShrink:0,minWidth:60}}>{res.id}</span>
        <div style={{flex:1,minWidth:0}}>
          <p style={{margin:0,fontSize:12,color:expanded?T.gold:"#aaa",fontFamily:T.serif,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{res.title}</p>
        </div>
        <span style={{fontSize:9,color:T.muted,fontFamily:T.mono,flexShrink:0}}>{res.circle}</span>
        <span style={{fontSize:9,color:T.textDim,fontFamily:T.mono,flexShrink:0,minWidth:72,textAlign:"right"}}>{res.adopted}</span>
        <span style={{fontSize:10,color:T.muted,marginLeft:4}}>{expanded?"▲":"▼"}</span>
      </div>
      {expanded&&(
        <div style={{padding:"0 16px 16px",borderTop:`1px solid #1a1505`}}>
          <p style={{margin:"12px 0 10px",fontSize:12,color:T.textSub,fontFamily:T.serif,lineHeight:1.7}}>{res.summary}</p>
          {res.references.length>0&&(
            <div style={{display:"flex",alignItems:"center",gap:6}}>
              <span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>References:</span>
              {res.references.map(r=>(
                <span key={r} style={{fontSize:9,color:`${T.gold}88`,fontFamily:T.mono,padding:"1px 7px",borderRadius:3,background:`${T.gold}12`,border:`1px solid ${T.gold}20`,cursor:"pointer"}}>{r}</span>
              ))}
            </div>
          )}
          <div style={{display:"flex",alignItems:"center",gap:6,marginTop:10,paddingTop:10,borderTop:`1px solid #1a1505`}}>
            <span style={{fontSize:9,color:`${T.gold}50`,fontFamily:T.mono,letterSpacing:1}}>⬡ IMMUTABLE</span>
            <span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>· Adopted by resolution, cannot be amended — only superseded</span>
          </div>
        </div>
      )}
    </div>
  );
}

function OrgDash(){
  const barData=ORG.domains.map(d=>({name:d.name.split(" ")[0],activity:d.activity}));
  const [expandedRes,setExpandedRes]=useState(null);
  return(
    <div style={{display:"flex",gap:20}}>
      <div style={{flex:1,minWidth:0}}>
        {/* Org profile */}
        <div style={{padding:"20px",borderRadius:8,border:`1px solid ${T.border}`,background:T.surface,marginBottom:20}}>
          <div style={{display:"flex",alignItems:"flex-start",gap:14}}>
            <div style={{width:44,height:44,borderRadius:8,background:"linear-gradient(135deg,#1a2030,#0a1020)",border:`1px solid ${T.goldDim}`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,color:T.gold,flexShrink:0}}>⊕</div>
            <div>
              <h2 style={{margin:"0 0 6px",fontSize:17,color:T.text,fontFamily:T.serif,fontWeight:400}}>{ORG.name}</h2>
              <p style={{margin:0,fontSize:12,color:T.textSub,fontFamily:T.serif,lineHeight:1.65}}>{ORG.mandate}</p>
            </div>
          </div>
        </div>

        {/* Domain activity */}
        <SectionHead label="Domain Activity" sub="Ws contribution volume"/>
        <div style={{height:130,marginBottom:24}}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={barData} barSize={18}>
              <XAxis dataKey="name" tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} axisLine={false} tickLine={false}/>
              <Tooltip contentStyle={{background:T.surface,border:`1px solid ${T.border2}`,borderRadius:6,fontFamily:"DM Mono",fontSize:10}} cursor={false}/>
              <Bar dataKey="activity" fill={T.gold} opacity={0.6} radius={[3,3,0,0]}/>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Circles */}
        <SectionHead label="Circles"/>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginBottom:28}}>
          {ORG.circles.map(c=>(
            <div key={c.name} style={{padding:"14px",borderRadius:7,border:`1px solid ${T.border}`,background:T.panel,cursor:"pointer"}}
              onMouseEnter={e=>e.currentTarget.style.borderColor=T.border2}
              onMouseLeave={e=>e.currentTarget.style.borderColor=T.border}
            >
              <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
                <span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>{c.members} members</span>
                <span style={{fontSize:9,color:c.motions>0?T.gold:T.muted,fontFamily:T.mono}}>{c.motions} active</span>
              </div>
              <p style={{margin:"0 0 10px",fontSize:13,color:"#bbb",fontFamily:T.serif,lineHeight:1.3}}>{c.name}</p>
              <div style={{display:"flex",alignItems:"center",gap:6}}>
                <BarMini pct={c.auditHealth} color={T.green}/>
                <span style={{fontSize:9,color:T.muted,fontFamily:T.mono,minWidth:28}}>{c.auditHealth}%</span>
              </div>
            </div>
          ))}
        </div>

        {/* Resolutions — immutable policy registry */}
        <SectionHead label="Resolutions" sub="Adopted policy · immutable · the organisation's codex"/>
        <div style={{marginBottom:28}}>
          {ORG.resolutions.map(r=>(
            <ResolutionCard key={r.id} res={r} expanded={expandedRes===r.id} onToggle={()=>setExpandedRes(expandedRes===r.id?null:r.id)}/>
          ))}
        </div>

        {/* Active motions — separate, clearly drafts */}
        <SectionHead label="Active Motions" sub="Proposals under deliberation · not yet adopted"/>
        {ORG.activeMotions.map(m=>(
          <div key={m.title} style={{display:"flex",alignItems:"center",gap:12,padding:"11px 0",borderBottom:`1px solid ${T.border}`}}>
            <StatusPill status={m.status}/>
            <p style={{margin:0,flex:1,fontSize:12,color:"#bbb",fontFamily:T.serif}}>{m.title}</p>
            <span style={{fontSize:10,color:T.muted,fontFamily:T.mono}}>{m.circle}</span>
            <span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>{m.date}</span>
          </div>
        ))}
      </div>

      {/* Right rail */}
      <div style={{width:236,flexShrink:0}}>
        <SectionHead label="Org Health"/>
        {Object.entries(ORG.health).map(([k,v])=>(
          <div key={k} style={{marginBottom:14}}>
            <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}>
              <span style={{fontSize:10,color:T.textDim,fontFamily:T.mono}}>{k.replace(/([A-Z])/g," $1").toLowerCase()}</span>
              <span style={{fontSize:10,color:T.gold,fontFamily:T.mono}}>{v}%</span>
            </div>
            <BarMini pct={v} color={v>85?T.green:v>70?T.gold:T.red}/>
          </div>
        ))}
        <div style={{marginTop:6,padding:"10px 12px",borderRadius:6,background:`${T.gold}08`,border:`1px solid ${T.gold}15`}}>
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:2}}>
            <span style={{fontSize:9,color:`${T.gold}70`,fontFamily:T.mono}}>Total resolutions</span>
            <span style={{fontSize:11,color:T.gold,fontFamily:T.mono}}>41</span>
          </div>
          <div style={{display:"flex",justifyContent:"space-between"}}>
            <span style={{fontSize:9,color:`${T.gold}70`,fontFamily:T.mono}}>Active motions</span>
            <span style={{fontSize:11,color:T.gold,fontFamily:T.mono}}>4</span>
          </div>
        </div>
        <div style={{marginTop:24}}>
          <SectionHead label="Prominent Curiosities"/>
          {ORG.curiosities.map(c=>(
            <div key={c.tag} style={{display:"flex",alignItems:"center",gap:8,padding:"7px 0",borderBottom:`1px solid ${T.border}`}}>
              <span style={{fontSize:10,color:T.muted,fontFamily:T.mono,flex:1}}>#{c.tag}</span>
              <BarMini pct={c.w*100} color={T.blue}/>
              <span style={{fontSize:9,color:T.textDim,fontFamily:T.mono,minWidth:24,textAlign:"right"}}>{Math.round(c.w*100)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CircleDash(){
  const barData=CIRCLE.domainActivity.map(d=>({name:d.name,activity:d.activity,mandate:d.mandate}));
  return(
    <div style={{display:"flex",gap:20}}>
      <div style={{flex:1,minWidth:0}}>
        <div style={{padding:"16px 20px",borderRadius:8,border:`1px solid ${T.border}`,background:T.surface,marginBottom:20}}>
          <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:8}}>
            <div style={{width:8,height:8,borderRadius:"50%",background:T.gold}}/>
            <h2 style={{margin:0,fontSize:16,color:T.text,fontFamily:T.serif,fontWeight:400}}>{CIRCLE.name}</h2>
            <Pill color={T.gold} bg={`${T.gold}15`}>{CIRCLE.members} members</Pill>
          </div>
          <p style={{margin:"0 0 10px",fontSize:12,color:T.textSub,fontFamily:T.serif,lineHeight:1.65}}>{CIRCLE.mandate}</p>
          <div style={{display:"flex",gap:6}}>{CIRCLE.domains.map(d=><DomainTag key={d} d={d} w={0.4}/>)}</div>
        </div>

        {/* Domain alignment graph */}
        <SectionHead label="Domain Activity" sub="Contribution volume · gold = within mandate, grey = adjacent"/>
        <div style={{height:120,marginBottom:8}}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={barData} barSize={20}>
              <XAxis dataKey="name" tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} axisLine={false} tickLine={false}/>
              <Tooltip contentStyle={{background:T.surface,border:`1px solid ${T.border2}`,borderRadius:6,fontFamily:"DM Mono",fontSize:10}} cursor={false}
                formatter={(v,n,p)=>[v,p.payload.mandate?"in mandate":"adjacent"]}
              />
              <Bar dataKey="activity" radius={[3,3,0,0]}
                shape={props=>{
                  const{x,y,width,height,payload}=props;
                  return <rect x={x} y={y} width={width} height={height} fill={payload.mandate?T.gold:"#2a2a2a"} opacity={payload.mandate?0.7:1} rx={3}/>;
                }}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div style={{display:"flex",gap:14,marginBottom:24,paddingLeft:4}}>
          <div style={{display:"flex",alignItems:"center",gap:4}}><div style={{width:10,height:2,background:T.gold,opacity:0.7}}/><span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>mandate domain</span></div>
          <div style={{display:"flex",alignItems:"center",gap:4}}><div style={{width:10,height:2,background:"#2a2a2a"}}/><span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>adjacent activity</span></div>
        </div>
        <SectionHead label="Circle Cells" sub="Motions and special business" action={{label:"+ New Cell",fn:()=>{}}}/>
          <div key={c.title} style={{padding:"14px 16px",borderRadius:7,border:`1px solid ${T.border}`,background:T.panel,marginBottom:7,cursor:"pointer"}}
            onMouseEnter={e=>e.currentTarget.style.borderColor=T.border2}
            onMouseLeave={e=>e.currentTarget.style.borderColor=T.border}
          >
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <p style={{margin:0,fontSize:13,color:"#bbb",fontFamily:T.serif}}>{c.title}</p>
              <div style={{display:"flex",alignItems:"center",gap:8}}>
                <span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>{c.participants} members · {c.age}</span>
                <StatusPill status={c.status}/>
              </div>
            </div>
          </div>
        ))}
        <SectionHead label="STF Cells" sub="Audit and executional STFs commissioned here"/>
        {CIRCLE.stfCells.map(s=>(
          <div key={s.title} style={{padding:"14px 16px",borderRadius:7,border:`1px solid ${T.border}`,background:T.surface,marginBottom:7}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:10}}>
              <p style={{margin:0,fontSize:12,color:"#bbb",fontFamily:T.serif}}>{s.title}</p>
              <StatusPill status={s.status}/>
            </div>
            <div style={{display:"flex",alignItems:"center",gap:10}}>
              <BarMini pct={s.progress} color={s.status==="concluded"?T.muted:T.blue}/>
              <span style={{fontSize:9,color:T.muted,fontFamily:T.mono,minWidth:60}}>{s.progress}% · {s.deadline}</span>
            </div>
          </div>
        ))}
      </div>
      <div style={{width:236,flexShrink:0}}>
        <SectionHead label="Circle Activity" sub="Domain-tagged feed"/>
        {CIRCLE.feed.map((f,i)=>(
          <div key={i} style={{padding:"10px 0",borderBottom:`1px solid ${T.border}`}}>
            <div style={{display:"flex",gap:8,marginBottom:4}}>
              <div style={{width:22,height:22,borderRadius:"50%",background:`${T.blue}20`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:9,color:T.blue,flexShrink:0}}>{f.author[0]}</div>
              <div style={{flex:1}}>
                <p style={{margin:"0 0 4px",fontSize:11,color:T.textSub,fontFamily:T.serif,lineHeight:1.4}}>
                  <span style={{color:"#ccc"}}>{f.author}</span> {f.action} <span style={{color:T.gold}}>{f.cell}</span>
                </p>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                  <DomainTag d={f.domain} w={f.w||0.3}/>
                  <span style={{fontSize:8,color:T.muted,fontFamily:T.mono}}>{f.time}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function STFDash(){
  const daysSpent=STF.daysTotal-STF.daysLeft;
  return(
    <div style={{display:"flex",gap:20}}>
      <div style={{flex:1,minWidth:0}}>
        <div style={{padding:"20px",borderRadius:8,border:`1px solid ${T.border}`,background:T.surface,marginBottom:20,position:"relative",overflow:"hidden"}}>
          <div style={{position:"absolute",top:0,left:0,right:0,height:2,background:`linear-gradient(90deg,${T.red},transparent)`}}/>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start"}}>
            <div>
              <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:6}}>
                <Pill color={T.red} bg={`${T.red}15`}>⚑ Audit STF</Pill>
                <span style={{fontSize:10,color:T.muted,fontFamily:T.mono}}>{STF.name}</span>
              </div>
              <p style={{margin:"0 0 8px",fontSize:15,color:T.text,fontFamily:T.serif}}>{STF.type}</p>
              <p style={{margin:"0 0 10px",fontSize:12,color:T.textSub,fontFamily:T.serif,lineHeight:1.65}}>{STF.mandate}</p>
              <div style={{display:"flex",gap:6}}>
                <Pill color={T.gold} bg={`${T.gold}15`}>↖ {STF.circle}</Pill>
                <Pill color={T.muted}>{STF.commissioned} → {STF.deadline}</Pill>
              </div>
            </div>
            <div style={{textAlign:"right",flexShrink:0,marginLeft:16}}>
              <p style={{margin:"0 0 4px",fontSize:28,color:STF.daysLeft<7?T.red:T.gold,fontFamily:T.mono}}>{STF.daysLeft}</p>
              <span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>days remaining</span>
            </div>
          </div>
          <div style={{marginTop:16}}>
            <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
              <span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>Work progress vs time elapsed</span>
              <span style={{fontSize:9,color:T.gold,fontFamily:T.mono}}>{STF.progress}% work · {Math.round((daysSpent/STF.daysTotal)*100)}% time</span>
            </div>
            <div style={{height:3,background:T.border,borderRadius:2,marginBottom:3}}>
              <div style={{width:`${STF.progress}%`,height:"100%",background:T.gold,borderRadius:2}}/>
            </div>
            <div style={{height:3,background:T.border,borderRadius:2}}>
              <div style={{width:`${(daysSpent/STF.daysTotal)*100}%`,height:"100%",background:`${T.blue}60`,borderRadius:2}}/>
            </div>
            <div style={{display:"flex",gap:14,marginTop:4}}>
              <div style={{display:"flex",alignItems:"center",gap:4}}><div style={{width:10,height:1.5,background:T.gold}}/><span style={{fontSize:8,color:T.muted,fontFamily:T.mono}}>work</span></div>
              <div style={{display:"flex",alignItems:"center",gap:4}}><div style={{width:10,height:1.5,background:`${T.blue}60`}}/><span style={{fontSize:8,color:T.muted,fontFamily:T.mono}}>time</span></div>
            </div>
          </div>
        </div>
        <SectionHead label="Metrics"/>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginBottom:24}}>
          {STF.metrics.map(m=>(
            <div key={m.label} style={{padding:"14px",borderRadius:7,border:`1px solid ${T.border}`,background:T.panel}}>
              <p style={{margin:"0 0 6px",fontSize:10,color:T.muted,fontFamily:T.mono}}>{m.label}</p>
              <p style={{margin:0,fontSize:16,color:T.text,fontFamily:T.mono}}>{m.value}</p>
              {m.pct&&<div style={{marginTop:8}}><BarMini pct={m.pct} color={T.blue}/></div>}
            </div>
          ))}
        </div>
        <SectionHead label="Audit Log" sub="Tamper-evident record" action={{label:"+ Entry",fn:()=>{}}}/>
        {STF.log.map((l,i)=>(
          <div key={i} style={{padding:"14px 16px",borderRadius:7,border:`1px solid ${T.border}`,background:T.surface,marginBottom:8}}>
            <p style={{margin:"0 0 6px",fontSize:12,color:"#bbb",fontFamily:T.serif,lineHeight:1.6}}>{l.entry}</p>
            <span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>{l.date}</span>
          </div>
        ))}
      </div>
      <div style={{width:236,flexShrink:0}}>
        <SectionHead label="Commissioning Cell"/>
        <div style={{padding:"12px 14px",borderRadius:7,border:`1px solid ${T.border}`,background:T.surface,marginBottom:20}}>
          <p style={{margin:"0 0 6px",fontSize:12,color:"#bbb",fontFamily:T.serif}}>{STF.parentCell}</p>
          <span style={{fontSize:9,color:T.muted,fontFamily:T.mono}}>Results published here on conclusion</span>
        </div>
        <SectionHead label="Members"/>
        {STF.members.map((m,i)=>(
          <div key={m} style={{display:"flex",alignItems:"center",gap:8,padding:"9px 0",borderBottom:`1px solid ${T.border}`}}>
            <div style={{width:24,height:24,borderRadius:"50%",background:`${T.red}20`,border:`1px solid ${T.red}30`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:10,color:T.red}}>{m[0]}</div>
            <span style={{fontSize:11,color:T.textSub,fontFamily:T.serif}}>{m}</span>
            {i===0&&<Pill color={T.gold} bg={`${T.gold}15`}>you</Pill>}
          </div>
        ))}
        <div style={{marginTop:24}}>
          <SectionHead label="Quorum"/>
          <div style={{padding:"12px 14px",borderRadius:7,background:`${T.green}10`,border:`1px solid ${T.green}25`}}>
            <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:4}}><Dot color={T.green}/><span style={{fontSize:11,color:T.green,fontFamily:T.mono}}>3/3 members active</span></div>
            <p style={{margin:0,fontSize:10,color:`${T.green}88`,fontFamily:T.serif,fontStyle:"italic"}}>All log entries valid.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

const CONTEXTS=[
  {key:"commons",label:"Commons",icon:"⬡",group:"root"},
  {key:"personal",label:"Amara Osei",icon:"◉",group:"personal"},
  {key:"org",label:"Orbis Collective",icon:"⊕",group:"org"},
  {key:"circle",label:"Protocol Engineering",icon:"◎",group:"circles"},
  {key:"stf",label:"aSTF-12",icon:"⚑",group:"stfs"},
];

const GROUP_LABELS={root:"",personal:"Personal",org:"Organisation",circles:"My Circles",stfs:"Active STFs"};

const TELEMETRY={
  commons:[[["Domain Ws · top"],[["Protocol Eng.","1780"],["UX Design","1870"],["Community","1720"]]],[["Active today"],[["Posts","4"],["Relays","2"],["Cells joined","1"]]]],
  personal:[[["Memberships"],[["Circles","2"],["Active STFs","1"],["Commons posts","42"]]],[["Pending"],[["Votes","2"],["STF log entry","1"],["Proposals","0"]]]], 
  org:[[["Org pulse"],[["Active motions","6"],["Open cells","11"],["Members online","14"]]],[["Audit status"],[["aSTFs active","4"],["Reports due","1"],["Anomalies open","3"]]]],
  circle:[[["Circle metrics"],[["Active motions","3"],["Members","8"],["Open STFs","1"]]],[["Your role"],[["Vote weight","1780"],["Last vote","2d ago"],["Ws delta (7d)","+48"]]]],
  stf:[[["STF status"],[["Days left","17"],["Progress","41%"],["Members","3/3"]]],[["Audit scope"],[["Posts reviewed","84"],["Anomalies","3"],["Calibrations","2"]]]],
};

function Telemetry({ctx}){
  const blocks=TELEMETRY[ctx]||TELEMETRY.commons;
  return(
    <div style={{flex:1,padding:"14px 14px",overflow:"auto"}}>
      {blocks.map(([[label],items])=>(
        <div key={label} style={{marginBottom:20}}>
          <p style={{margin:"0 0 10px",fontSize:8,fontFamily:T.mono,letterSpacing:2,textTransform:"uppercase",color:T.muted}}>{label}</p>
          {items.map(([k,v])=>(
            <div key={k} style={{display:"flex",justifyContent:"space-between",padding:"6px 0",borderBottom:`1px solid ${T.border}`}}>
              <span style={{fontSize:10,color:T.textDim,fontFamily:T.mono}}>{k}</span>
              <span style={{fontSize:10,color:T.gold,fontFamily:T.mono}}>{v}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export default function App(){
  const [ctx,setCtx]=useState("commons");
  const views={commons:<CommonsDash/>,personal:<PersonalDash/>,org:<OrgDash/>,circle:<CircleDash/>,stf:<STFDash/>};
  const activeCtx=CONTEXTS.find(c=>c.key===ctx);
  const groups=[...new Set(CONTEXTS.map(c=>c.group))];
  const subtitles={root:"Open commons · all members",personal:"Your identity and contribution history",org:"Organisation codex · universally readable",circles:"Circle dashboard · members only",stfs:"STF dashboard · active mandate · expires Mar 15"};

  return(
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=Lora:ital,wght@0,400;0,500;1,400;1,500&display=swap');
        *{box-sizing:border-box;}body{margin:0;background:${T.bg};}
        ::-webkit-scrollbar{width:3px;height:3px;}::-webkit-scrollbar-track{background:${T.bg};}::-webkit-scrollbar-thumb{background:${T.dim};}
      `}</style>
      <div style={{display:"flex",height:"100vh",background:T.bg,color:T.text,overflow:"hidden"}}>

        {/* COL 1 */}
        <div style={{width:208,borderRight:`1px solid ${T.border}`,display:"flex",flexDirection:"column",background:T.surface,flexShrink:0}}>
          <div style={{padding:"18px 18px 14px",borderBottom:`1px solid ${T.border}`}}>
            <div style={{display:"flex",alignItems:"baseline",gap:7}}>
              <span style={{fontFamily:T.mono,fontSize:14,letterSpacing:3,color:T.gold,fontWeight:500}}>PAAS</span>
              <span style={{fontFamily:T.serif,fontSize:10,color:T.muted,fontStyle:"italic"}}>Orbis</span>
            </div>
          </div>
          <div style={{padding:"12px 10px",borderBottom:`1px solid ${T.border}`}}>
            {groups.map(g=>{
              const items=CONTEXTS.filter(c=>c.group===g);
              return(
                <div key={g} style={{marginBottom:6}}>
                  {GROUP_LABELS[g]&&<p style={{margin:"6px 4px 4px",fontSize:7,fontFamily:T.mono,letterSpacing:2,textTransform:"uppercase",color:T.dim}}>{GROUP_LABELS[g]}</p>}
                  {items.map(item=>(
                    <button key={item.key} onClick={()=>setCtx(item.key)} style={{
                      width:"100%",display:"flex",alignItems:"center",gap:8,
                      padding:"7px 10px",borderRadius:5,border:"none",cursor:"pointer",
                      background:ctx===item.key?T.panel:"transparent",
                      color:ctx===item.key?T.gold:T.textDim,
                      transition:"all 0.12s",textAlign:"left"
                    }}>
                      <span style={{fontSize:11,fontFamily:T.mono,width:14,textAlign:"center",flexShrink:0}}>{item.icon}</span>
                      <span style={{fontSize:11,fontFamily:T.mono,letterSpacing:0.2,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{item.label}</span>
                      {ctx===item.key&&<div style={{marginLeft:"auto",width:3,height:3,borderRadius:"50%",background:T.gold,flexShrink:0}}/>}
                    </button>
                  ))}
                </div>
              );
            })}
          </div>
          <Telemetry ctx={ctx}/>
          <div style={{padding:"12px 18px",borderTop:`1px solid ${T.border}`}}>
            <p style={{margin:0,fontSize:8,color:T.dim,fontFamily:T.mono,lineHeight:1.9}}>Autonomy → Audit<br/>Audit → Action<br/>Action → Learning</p>
          </div>
        </div>

        {/* COL 2+3 */}
        <div style={{flex:1,overflow:"auto",padding:"26px 30px",display:"flex",flexDirection:"column"}}>
          <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:26}}>
            <span style={{fontSize:13,color:T.gold,fontFamily:T.mono}}>{activeCtx?.icon}</span>
            <div>
              <h1 style={{margin:0,fontSize:11,fontFamily:T.mono,letterSpacing:2,textTransform:"uppercase",color:T.gold}}>{activeCtx?.label}</h1>
              <p style={{margin:0,fontSize:9,color:T.muted,fontFamily:T.mono,letterSpacing:0.5}}>{subtitles[activeCtx?.group]}</p>
            </div>
          </div>
          {views[ctx]}
        </div>
      </div>
    </>
  );
}
