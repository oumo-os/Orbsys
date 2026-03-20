"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/stores/auth";
import { membersApi } from "@/lib/api";
import {
  MessageSquare, Layers, FileText, Shield, Hash,
  Circle, Users, BarChart2, LogOut, Bell,
} from "lucide-react";

const NAV = [
  { href: "/org/commons",    label: "Commons",    icon: MessageSquare },
  { href: "/org/cells",      label: "Cells",      icon: Layers },
  { href: "/org/motions",    label: "Motions",    icon: FileText },
  { href: "/org/stf",        label: "STF",        icon: Shield },
  { href: "/org/circles",    label: "Circles",    icon: Circle },
  { href: "/org/members",    label: "Members",    icon: Users },
  { href: "/org/competence", label: "Competence", icon: BarChart2 },
  { href: "/org/ledger",     label: "Ledger",     icon: Hash },
];

const STATE_COLOURS: Record<string, string> = {
  active:       "text-emerald-400",
  probationary: "text-yellow-400",
  suspended:    "text-red-400",
  exited:       "text-zinc-500",
};

export default function OrgLayout({ children }: { children: React.ReactNode }) {
  const router   = useRouter();
  const pathname = usePathname();
  const { member, isAuthenticated, isHydrated, hydrate, clearAuth } = useAuthStore();

  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotifs, setShowNotifs]   = useState(false);
  const [notifs, setNotifs]           = useState<{
    id: string; priority: string; notification_type: string;
    body: string; action_url?: string; read: boolean; created_at: string;
  }[]>([]);

  useEffect(() => { if (!isHydrated) hydrate(); }, [isHydrated, hydrate]);

  useEffect(() => {
    if (isHydrated && !isAuthenticated) router.replace("/auth/login");
  }, [isHydrated, isAuthenticated, router]);

  // Poll unread count every 30 seconds
  useEffect(() => {
    if (!isAuthenticated) return;
    const fetchUnread = () => {
      membersApi.notifications({ unread_only: true, page: 1, page_size: 10 })
        .then(r => {
          const data = r.data as { items?: typeof notifs; total?: number };
          setUnreadCount(data.total ?? 0);
          if (data.items) setNotifs(data.items);
        })
        .catch(() => {});
    };
    fetchUnread();
    const iv = setInterval(fetchUnread, 30000);
    return () => clearInterval(iv);
  }, [isAuthenticated]);

  async function markAllRead() {
    try {
      await membersApi.markAllRead();
      setUnreadCount(0);
      setNotifs(n => n.map(x => ({ ...x, read: true })));
    } catch {}
  }

  function handleSignOut() {
    clearAuth();
    router.replace("/auth/login");
  }

  if (!isHydrated) {
    return (
      <div className="min-h-screen bg-[var(--void)] flex items-center justify-center">
        <div className="w-5 h-5 border border-[var(--gold)]/40 border-t-[var(--gold)]
          rounded-full animate-spin" />
      </div>
    );
  }
  if (!isAuthenticated) return null;

  const PRIORITY_DOT: Record<string, string> = {
    p1: "bg-red-400", p2: "bg-amber-400", p3: "bg-zinc-500",
  };

  function relTime(iso: string) {
    const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
    if (m < 60) return `${m}m`;
    if (m < 1440) return `${Math.floor(m / 60)}h`;
    return `${Math.floor(m / 1440)}d`;
  }

  return (
    <div className="flex h-screen bg-[var(--void)] overflow-hidden">
      {/* ── Sidebar ───────────────────────────────────────────────────────── */}
      <aside className="w-[220px] flex-shrink-0 flex flex-col border-r
        border-[var(--border)] bg-[var(--surface)]">

        {/* Logo + notification bell */}
        <div className="px-5 py-4 border-b border-[var(--border)]
          flex items-center justify-between">
          <div>
            <span className="font-display font-bold text-base text-[var(--gold)]
              tracking-tight">
              Orb Sys
            </span>
            {member && (
              <p className="font-mono text-[10px] text-[var(--text-muted)] mt-0.5 truncate
                max-w-[130px]">
                {member.handle}
              </p>
            )}
          </div>

          {/* Notification bell */}
          <div className="relative">
            <button
              onClick={() => setShowNotifs(!showNotifs)}
              className="relative p-1.5 rounded text-[var(--text-muted)]
                hover:text-[var(--text)] hover:bg-[var(--surface-raised)]
                transition-colors"
            >
              <Bell size={13} />
              {unreadCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 rounded-full
                  bg-red-500 text-white text-[8px] font-mono flex items-center
                  justify-center leading-none">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </button>

            {/* Notification dropdown */}
            {showNotifs && (
              <div className="absolute right-0 top-full mt-2 w-72 z-50
                bg-[var(--surface)] border border-[var(--border)] rounded-lg
                shadow-xl overflow-hidden">
                <div className="flex items-center justify-between px-3 py-2
                  border-b border-[var(--border)]">
                  <span className="text-[10px] font-mono text-[var(--text-muted)]
                    uppercase tracking-wider">
                    Notifications
                  </span>
                  {unreadCount > 0 && (
                    <button onClick={markAllRead}
                      className="text-[9px] font-mono text-[var(--gold)]
                        hover:underline">
                      Mark all read
                    </button>
                  )}
                </div>

                <div className="max-h-72 overflow-y-auto">
                  {notifs.length === 0 ? (
                    <div className="px-3 py-6 text-center">
                      <p className="text-[11px] font-mono text-[var(--text-dim)]">
                        No notifications
                      </p>
                    </div>
                  ) : notifs.map(n => (
                    <div key={n.id}
                      onClick={() => {
                        setShowNotifs(false);
                        if (n.action_url) router.push(n.action_url);
                      }}
                      className={`px-3 py-2.5 border-b border-[var(--border)]
                        last:border-0 cursor-pointer transition-colors
                        hover:bg-[var(--surface-raised)]
                        ${n.read ? "opacity-60" : ""}`}>
                      <div className="flex items-start gap-2">
                        <div className={`w-1.5 h-1.5 rounded-full mt-1 shrink-0
                          ${PRIORITY_DOT[n.priority] ?? "bg-zinc-500"}`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-[11px] text-[var(--text)] leading-snug
                            line-clamp-2">
                            {n.body}
                          </p>
                          <p className="text-[9px] font-mono text-[var(--text-dim)] mt-0.5">
                            {relTime(n.created_at)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-2 overflow-y-auto">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                className={`
                  flex items-center gap-2.5 px-5 py-[7px] text-[13px] transition-all
                  border-l-2 no-underline
                  ${active
                    ? "font-medium text-[var(--text)] bg-[var(--surface-raised)] border-[var(--gold)]"
                    : "font-normal text-[var(--text-muted)] border-transparent hover:text-[var(--text)]"
                  }
                `}
              >
                <Icon size={13} className={active ? "text-[var(--gold)]" : ""} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Member footer */}
        <div className="px-5 py-3 border-t border-[var(--border)] space-y-2">
          {member && (
            <div>
              <p className="font-mono text-[11px] text-[var(--text)] truncate">
                {member.display_name}
              </p>
              <p className={`font-mono text-[10px] capitalize
                ${STATE_COLOURS[member.current_state] ?? "text-[var(--text-muted)]"}`}>
                {member.current_state}
              </p>
            </div>
          )}
          <button
            onClick={handleSignOut}
            className="flex items-center gap-1.5 text-[11px] font-mono
              text-[var(--text-muted)] hover:text-red-400 transition-colors"
          >
            <LogOut size={11} />
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto" onClick={() => setShowNotifs(false)}>
        <div className="max-w-4xl mx-auto px-6 py-6">
          {children}
        </div>
      </main>
    </div>
  );
}
