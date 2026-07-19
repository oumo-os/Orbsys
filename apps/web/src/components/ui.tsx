"use client";

export const T = {
  bg:"#050505",surface:"#080808",panel:"#0b0b0b",border:"#141414",border2:"#1e1e1e",
  gold:"#c8a96e",goldDim:"#c8a96e40",green:"#6ea880",blue:"#6e8dc8",red:"#c87a6e",
  muted:"#3a3a3a",dim:"#252525",text:"#cccccc",textSub:"#888888",textDim:"#555555",
  mono:"'DM Mono', monospace",serif:"'Lora', serif",
};

export const Pill = ({ children, color = T.muted, bg = "#111" }: {
  children: React.ReactNode; color?: string; bg?: string;
}) => (
  <span style={{
    display:"inline-flex", alignItems:"center", gap:4,
    padding:"2px 9px", borderRadius:20, background:bg, color,
    fontSize:10, fontFamily:T.mono, letterSpacing:0.4, whiteSpace:"nowrap",
  }}>{children}</span>
);

export const Dot = ({ color }: { color: string }) => (
  <span style={{
    width:5, height:5, borderRadius:"50%", background:color,
    display:"inline-block", flexShrink:0,
  }}/>
);

export const BarMini = ({ pct, color = T.gold }: { pct: number; color?: string }) => (
  <div style={{ flex:1, height:2, background:T.border, borderRadius:1 }}>
    <div style={{
      width:`${pct}%`, height:"100%", background:color,
      borderRadius:1, transition:"width 1.2s ease",
    }}/>
  </div>
);

const STATUS_MAP: Record<string, [string, string, string, string]> = {
  deliberating:["Deliberating","#1a2a1a","#6ea880","#4ea860"],
  drafting:["Drafting","#1a1f2a","#6e8dc8","#4e70c8"],
  finalising:["Finalising","#2a231a","#c8a96e","#c89040"],
  resolved:["Resolved","#1a1a1a","#555","#444"],
  active:["Active","#1a2a1a","#6ea880","#4ea860"],
  concluded:["Concluded","#1a1a1a","#555","#444"],
  pending:["Pending","#1a1f2a","#6e8dc8","#4e70c8"],
  open:["Open","#1a1f2a","#6e8dc8","#4e70c8"],
  closed:["Closed","#1a1a1a","#555","#444"],
  probationary:["Probationary","#2a231a","#c8a96e","#c89040"],
  active_member:["Active","#1a2a1a","#6ea880","#4ea860"],
  exited:["Exited","#1a1a1a","#555","#444"],
  suspended:["Suspended","#2a1a1a","#c87a6e","#c86050"],
};

export const StatusPill = ({ status }: { status: string }) => {
  const s = STATUS_MAP[status] || STATUS_MAP.drafting;
  const [label, bg, color, dot] = s;
  return (
    <span style={{
      display:"inline-flex", alignItems:"center", gap:5,
      padding:"2px 9px", borderRadius:20, background:bg, color,
      fontSize:9, fontFamily:T.mono, letterSpacing:0.5,
    }}><Dot color={dot}/>{label}</span>
  );
};

export const SectionHead = ({ label, sub, action }: {
  label: string; sub?: string; action?: { label: string; fn: () => void };
}) => (
  <div style={{
    display:"flex", justifyContent:"space-between", alignItems:"flex-end",
    marginBottom:18, paddingBottom:12, borderBottom:`1px solid ${T.border}`,
  }}>
    <div>
      <p style={{
        margin:0, fontSize:9, fontFamily:T.mono, letterSpacing:2,
        textTransform:"uppercase", color:T.gold,
      }}>{label}</p>
      {sub && <p style={{
        margin:"4px 0 0", fontSize:11, color:T.muted,
        fontFamily:T.serif, fontStyle:"italic",
      }}>{sub}</p>}
    </div>
    {action && (
      <button onClick={action.fn} style={{
        padding:"5px 12px", border:`1px solid ${T.border2}`,
        borderRadius:5, background:"transparent", color:T.textDim,
        fontFamily:T.mono, fontSize:9, cursor:"pointer",
        letterSpacing:1, textTransform:"uppercase",
      }}>{action.label}</button>
    )}
  </div>
);

export const DomainTag = ({ d, w }: { d: string; w?: number | null }) => {
  const weight = w ?? 0;
  const alpha = Math.round((weight / 0.4) * 60 + 15);
  return (
    <span style={{
      display:"inline-flex", alignItems:"center", gap:4,
      padding:"2px 8px", borderRadius:20,
      background:`${T.blue}18`, border:`1px solid ${T.blue}${alpha.toString(16)}`,
      color:`${T.blue}cc`, fontSize:9, fontFamily:T.mono,
    }}>{d}{w != null && <span style={{color:`${T.blue}88`}}>{w.toFixed(2)}</span>}</span>
  );
};
