"use client";

import { useEffect, useState, useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth";
import { membersApi, circlesApi, stfApi } from "@/lib/api";
import { T, Dot } from "@/components/ui";

interface NavContext {
  key: string;
  label: string;
  icon: string;
  group: string;
  href: string;
}

const GROUP_LABELS: Record<string, string> = {
  "": "",
  personal: "Personal",
  org: "Organisation",
  circles: "My Circles",
  stfs: "Active STFs",
};

const SUBTITLES: Record<string, string> = {
  "": "Open commons · all members",
  personal: "Your identity and contribution history",
  org: "Organisation codex · universally readable",
  circles: "Circle dashboard · members only",
  stfs: "STF dashboard · active mandate",
};

export default function OrgLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { member, isAuthenticated, logout } = useAuthStore();

  const [circles, setCircles] = useState<{ id: string; name: string }[]>([]);
  const [activeStfs, setActiveStfs] = useState<{ id: string; mandate: string }[]>([]);
  const [unread, setUnread] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const [cRes, sRes, nRes] = await Promise.allSettled([
        circlesApi.list(),
        stfApi.list({ state: "active", page_size: 5 }),
        membersApi.notifications({ unread_only: true, page_size: 1 }),
      ]);
      if (cRes.status === "fulfilled")
        setCircles((cRes.value.data?.items ?? cRes.value.data ?? []).slice(0, 8));
      if (sRes.status === "fulfilled")
        setActiveStfs((sRes.value.data?.items ?? []).slice(0, 5));
      if (nRes.status === "fulfilled")
        setUnread(nRes.value.data?.total ?? 0);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) { router.replace("/auth/login"); return; }
    refresh();
    const iv = setInterval(refresh, 30000);
    return () => clearInterval(iv);
  }, [isAuthenticated, refresh, router]);

  if (!isAuthenticated || !member) return null;

  const contexts: NavContext[] = [
    { key: "commons", label: "Commons", icon: "⬡", group: "", href: "/org/commons" },
    { key: "personal", label: member.display_name || member.handle, icon: "◉", group: "personal", href: "/me" },
    { key: "org", label: member.org_name || "Organisation", icon: "⊕", group: "org", href: "/org" },
    ...circles.map(c => ({
      key: `circle-${c.id}`, label: c.name, icon: "◎",
      group: "circles", href: `/org/circles/${c.id}`,
    })),
    ...activeStfs.map(s => ({
      key: `stf-${s.id}`, label: s.mandate.slice(0, 20) + (s.mandate.length > 20 ? "…" : ""),
      icon: "⚑", group: "stfs", href: `/org/stf/${s.id}`,
    })),
  ];

  const activeContext = contexts.find(c => pathname.startsWith(c.href)) || contexts[0];
  const groups = [...new Set(contexts.map(c => c.group))];
  const subtitle = SUBTITLES[activeContext?.group ?? ""] || "";

  return (
    <div style={{ display:"flex", height:"100vh", background:T.bg, color:T.text, overflow:"hidden" }}>

      {/* ── COL 1: Sidebar ───────────────────────────────────────── */}
      <div style={{
        width:208, borderRight:`1px solid ${T.border}`,
        display:"flex", flexDirection:"column",
        background:T.surface, flexShrink:0,
      }}>
        {/* Branding */}
        <div style={{ padding:"18px 18px 14px", borderBottom:`1px solid ${T.border}` }}>
          <div style={{ display:"flex", alignItems:"baseline", gap:7 }}>
            <span style={{ fontFamily:T.mono, fontSize:14, letterSpacing:3, color:T.gold, fontWeight:500 }}>PAAS</span>
            <span style={{ fontFamily:T.serif, fontSize:10, color:T.muted, fontStyle:"italic" }}>Orbis</span>
          </div>
        </div>

        {/* Context Switcher */}
        <div style={{ padding:"12px 10px", borderBottom:`1px solid ${T.border}` }}>
          {groups.map(g => {
            const items = contexts.filter(c => c.group === g);
            return (
              <div key={g} style={{ marginBottom:6 }}>
                {GROUP_LABELS[g] && (
                  <p style={{
                    margin:"6px 4px 4px", fontSize:7, fontFamily:T.mono,
                    letterSpacing:2, textTransform:"uppercase", color:T.dim,
                  }}>{GROUP_LABELS[g]}</p>
                )}
                {items.map(item => {
                  const isActive = activeContext?.key === item.key;
                  return (
                    <button key={item.key} onClick={() => router.push(item.href)} style={{
                      width:"100%", display:"flex", alignItems:"center", gap:8,
                      padding:"7px 10px", borderRadius:5, border:"none", cursor:"pointer",
                      background:isActive ? T.panel : "transparent",
                      color:isActive ? T.gold : T.textDim,
                      transition:"all 0.12s", textAlign:"left",
                    }}>
                      <span style={{
                        fontSize:11, fontFamily:T.mono, width:14,
                        textAlign:"center", flexShrink:0,
                      }}>{item.icon}</span>
                      <span style={{
                        fontSize:11, fontFamily:T.mono, letterSpacing:0.2,
                        overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap",
                      }}>{item.label}</span>
                      {isActive && (
                        <div style={{
                          marginLeft:"auto", width:3, height:3,
                          borderRadius:"50%", background:T.gold, flexShrink:0,
                        }}/>
                      )}
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>

        {/* Notifications badge */}
        {unread > 0 && (
          <div style={{ padding:"8px 18px", borderBottom:`1px solid ${T.border}` }}>
            <button onClick={() => router.push("/org/members")} style={{
              width:"100%", display:"flex", alignItems:"center", gap:6,
              padding:"5px 8px", borderRadius:4, border:`1px solid ${T.gold}20`,
              background:`${T.gold}08`, cursor:"pointer",
            }}>
              <Dot color={T.gold}/>
              <span style={{ fontSize:9, color:T.gold, fontFamily:T.mono }}>
                {unread} unread notification{unread > 1 ? "s" : ""}
              </span>
            </button>
          </div>
        )}

        {/* Footer */}
        <div style={{ marginTop:"auto", padding:"12px 18px", borderTop:`1px solid ${T.border}` }}>
          <p style={{
            margin:0, fontSize:8, color:T.dim, fontFamily:T.mono, lineHeight:1.9,
          }}>Autonomy → Audit<br/>Audit → Action<br/>Action → Learning</p>
        </div>
      </div>

      {/* ── COL 2+3: Content ─────────────────────────────────────── */}
      <div style={{
        flex:1, overflow:"auto", padding:"26px 30px",
        display:"flex", flexDirection:"column",
      }}>
        {/* Page Header */}
        <div style={{
          display:"flex", alignItems:"center", gap:12, marginBottom:26,
        }}>
          <span style={{ fontSize:13, color:T.gold, fontFamily:T.mono }}>{activeContext?.icon}</span>
          <div>
            <h1 style={{
              margin:0, fontSize:11, fontFamily:T.mono, letterSpacing:2,
              textTransform:"uppercase", color:T.gold,
            }}>{activeContext?.label}</h1>
            <p style={{
              margin:0, fontSize:9, color:T.muted, fontFamily:T.mono, letterSpacing:0.5,
            }}>{subtitle}</p>
          </div>
          {/* Sign out */}
          <div style={{ marginLeft:"auto" }}>
            <button onClick={() => { logout(); router.replace("/auth/login"); }} style={{
              background:"none", border:"none", cursor:"pointer",
              fontSize:8, color:T.dim, fontFamily:T.mono,
              letterSpacing:1, textTransform:"uppercase", padding:0,
            }}>Sign out</button>
          </div>
        </div>

        {children}
      </div>
    </div>
  );
}
