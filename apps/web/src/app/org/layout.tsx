"use client";

import { useEffect, useState, useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/stores/auth";
import { membersApi, circlesApi, stfApi } from "@/lib/api";

const T = {
  bg:        "#050505",
  surface:   "#080808",
  raised:    "#0c0c0c",
  border:    "#141414",
  borderSub: "#0f0f0f",
  gold:      "#c8a96e",
  goldDim:   "#c8a96e30",
  dim:       "#2a2a2a",
  muted:     "#555555",
  textDim:   "#3a3a3a",
  text:      "#cccccc",
  textSub:   "#777777",
  green:     "#5a8a6a",
  mono:      "'DM Mono', monospace",
  serif:     "'Lora', serif",
};

interface NavSection {
  group: string;
  items: { key: string; label: string; href: string; badge?: number }[];
}

export default function OrgLayout({ children }: { children: React.ReactNode }) {
  const pathname  = usePathname();
  const router    = useRouter();
  const { member, isAuthenticated, logout } = useAuthStore();

  const [circles,        setCircles]        = useState<{ id: string; name: string }[]>([]);
  const [activeStfs,     setActiveStfs]     = useState<{ id: string; mandate: string }[]>([]);
  const [unread,         setUnread]         = useState(0);
  const [pendingApps,    setPendingApps]    = useState(0);

  // Fetch dynamic nav data
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

    try {
      const appRes = await membersApi.applications({ status: "pending", page_size: 1 });
      setPendingApps(appRes.data?.total ?? 0);
    } catch { /* not a circle member — ignore */ }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) { router.replace("/auth/login"); return; }
    refresh();
    const iv = setInterval(refresh, 30000);
    return () => clearInterval(iv);
  }, [isAuthenticated, refresh, router]);

  if (!isAuthenticated || !member) return null;

  // Build nav sections matching the mockup's group structure
  const navSections: NavSection[] = [
    {
      group: "",
      items: [
        { key: "commons",    label: "Commons",     href: "/org/commons" },
        { key: "cells",      label: "Cells",       href: "/org/cells" },
        { key: "motions",    label: "Motions",     href: "/org/motions" },
      ],
    },
    {
      group: "Organisation",
      items: [
        { key: "circles",    label: "Circles",     href: "/org/circles" },
        { key: "members",    label: "Members",     href: "/org/members",
          badge: pendingApps > 0 ? pendingApps : undefined },
        { key: "competence", label: "Competence",  href: "/org/competence" },
        { key: "ledger",     label: "Ledger",      href: "/org/ledger" },
      ],
    },
    ...(circles.length > 0 ? [{
      group: "My Circles",
      items: circles.map(c => ({
        key: `circle-${c.id}`,
        label: c.name,
        href: `/org/circles/${c.id}`,
      })),
    }] : []),
    ...(activeStfs.length > 0 ? [{
      group: "Active STFs",
      items: activeStfs.map(s => ({
        key: `stf-${s.id}`,
        label: s.mandate.slice(0, 28) + (s.mandate.length > 28 ? "…" : ""),
        href: `/org/stf/${s.id}`,
      })),
    }] : []),
  ];

  const isActive = (href: string) =>
    pathname === href || (href !== "/org/commons" && pathname.startsWith(href));

  return (
    <div style={{
      display: "flex", height: "100vh", overflow: "hidden",
      background: T.bg, fontFamily: T.mono, color: T.text,
    }}>

      {/* ── Left sidebar ─────────────────────────────────────────────── */}
      <div style={{
        width: 208, flexShrink: 0,
        background: T.surface,
        borderRight: `1px solid ${T.border}`,
        display: "flex", flexDirection: "column",
        height: "100vh", overflow: "hidden",
      }}>

        {/* Org identity */}
        <div style={{
          padding: "16px 14px 12px",
          borderBottom: `1px solid ${T.border}`,
        }}>
          <p style={{ margin: "0 0 1px", fontSize: 9, color: T.muted,
            letterSpacing: 3, textTransform: "uppercase" }}>
            {member.org_name ?? "Org Sys"}
          </p>
          <p style={{ margin: 0, fontSize: 13, color: T.gold, fontFamily: T.serif }}>
            {member.display_name_org ?? member.display_name}
          </p>
          <p style={{ margin: "2px 0 0", fontSize: 9, color: T.textSub }}>
            @{member.handle} · {member.current_state}
          </p>
        </div>

        {/* Navigation */}
        <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
          {navSections.map((section) => (
            <div key={section.group} style={{ marginBottom: 4 }}>
              {section.group && (
                <p style={{
                  margin: "10px 14px 4px",
                  fontSize: 7, color: T.muted,
                  letterSpacing: 2, textTransform: "uppercase",
                }}>
                  {section.group}
                </p>
              )}
              {section.items.map((item) => {
                const active = isActive(item.href);
                return (
                  <Link key={item.key} href={item.href} style={{ textDecoration: "none" }}>
                    <div style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "5px 14px",
                      background: active ? T.dim : "transparent",
                      borderLeft: `2px solid ${active ? T.gold : "transparent"}`,
                      cursor: "pointer",
                      transition: "background 0.1s",
                    }}
                      onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "#111"; }}
                      onMouseLeave={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                    >
                      <span style={{
                        fontSize: 11, color: active ? T.text : T.textSub,
                        fontFamily: T.mono,
                      }}>
                        {item.label}
                      </span>
                      {item.badge != null && (
                        <span style={{
                          fontSize: 8, padding: "1px 5px", borderRadius: 10,
                          background: T.gold, color: T.bg, fontFamily: T.mono,
                        }}>
                          {item.badge}
                        </span>
                      )}
                    </div>
                  </Link>
                );
              })}
            </div>
          ))}
        </div>

        {/* Bottom: notifications + profile */}
        <div style={{ borderTop: `1px solid ${T.border}`, padding: "10px 14px" }}>
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            marginBottom: 6,
          }}>
            <Link href="/me" style={{ textDecoration: "none" }}>
              <span style={{ fontSize: 10, color: T.textSub }}>
                ↗ My account
              </span>
            </Link>
            {unread > 0 && (
              <Link href="/org/members" style={{ textDecoration: "none" }}>
                <span style={{
                  fontSize: 8, padding: "2px 6px", borderRadius: 10,
                  background: T.goldDim, border: `1px solid ${T.gold}60`,
                  color: T.gold, fontFamily: T.mono,
                }}>
                  {unread} unread
                </span>
              </Link>
            )}
          </div>
          <button
            onClick={() => { logout(); router.replace("/auth/login"); }}
            style={{
              background: "none", border: "none", cursor: "pointer",
              fontSize: 9, color: T.muted, fontFamily: T.mono,
              letterSpacing: 1, textTransform: "uppercase", padding: 0,
            }}
          >
            Sign out
          </button>
        </div>
      </div>

      {/* ── Main content ──────────────────────────────────────────────── */}
      <div style={{
        flex: 1, display: "flex", flexDirection: "column",
        overflow: "hidden", background: T.bg,
      }}>
        {/* Page header bar */}
        <div style={{
          height: 36, flexShrink: 0,
          borderBottom: `1px solid ${T.border}`,
          display: "flex", alignItems: "center",
          padding: "0 20px",
          background: T.surface,
        }}>
          <p style={{ margin: 0, fontSize: 9, color: T.muted,
            letterSpacing: 2, textTransform: "uppercase", fontFamily: T.mono }}>
            {pathname.split("/").filter(Boolean).slice(1).join(" · ")}
          </p>
        </div>

        {/* Scrollable content */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px" }}>
          {children}
        </div>
      </div>
    </div>
  );
}
