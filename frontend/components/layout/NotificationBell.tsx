"use client";

// Top-bar notifications: things you started that have finished or failed
// (session analysis, example video, practice feedback). Polls while signed in.

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, CheckCheck, CircleAlert, CircleCheck } from "lucide-react";
import { notificationService, type AppNotification } from "@/services/notifications";
import { authService } from "@/services/auth";

const POLL_MS = 20_000;

function ago(iso: string) {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return new Date(iso).toLocaleDateString("en-MY", { day: "numeric", month: "short" });
}

export default function NotificationBell() {
  const router = useRouter();
  const [items, setItems] = useState<AppNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const refresh = useCallback(() => {
    if (!authService.isSignedIn()) return;
    notificationService.list().then((r) => { setItems(r.items); setUnread(r.unread); }).catch(() => null);
  }, []);

  // Poll, and check again whenever the tab regains focus
  useEffect(() => {
    const first = setTimeout(refresh, 0);
    const timer = setInterval(refresh, POLL_MS);
    window.addEventListener("focus", refresh);
    return () => { clearTimeout(first); clearInterval(timer); window.removeEventListener("focus", refresh); };
  }, [refresh]);

  // Close on outside click / Escape
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (!panelRef.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const openItem = async (n: AppNotification) => {
    setOpen(false);
    if (!n.read) {
      setItems((list) => list.map((x) => (x.id === n.id ? { ...x, read: true } : x)));
      setUnread((u) => Math.max(0, u - 1));
      notificationService.markRead(n.id).catch(() => null);
    }
    if (n.link) router.push(n.link);
  };

  const markAll = async () => {
    setItems((list) => list.map((x) => ({ ...x, read: true })));
    setUnread(0);
    await notificationService.markAllRead().catch(() => null);
  };

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => { setOpen((v) => !v); if (!open) refresh(); }}
        aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
        aria-expanded={open}
        className="relative w-9 h-9 flex items-center justify-center transition-colors hover:bg-[var(--surface-2)]"
        style={{ color: "var(--ink-2)" }}
      >
        <Bell className="w-4 h-4" />
        {unread > 0 && (
          <span className="absolute top-1 right-0.5 min-w-4 h-4 px-1 text-[10px] font-semibold leading-4 text-center text-white"
            style={{ background: "#C2342C" }}>
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute left-0 top-11 w-[min(360px,calc(100vw-2rem))] z-50"
          style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow-modal)" }}>
          <div className="flex items-center justify-between px-4 py-2.5" style={{ borderBottom: "1px solid var(--line)" }}>
            <p className="text-sm font-semibold text-[var(--ink)]">Notifications</p>
            {unread > 0 && (
              <button onClick={markAll} className="flex items-center gap-1 text-xs text-[var(--accent-ink)] hover:underline">
                <CheckCheck className="w-3.5 h-3.5" /> Mark all read
              </button>
            )}
          </div>
          {!authService.isSignedIn() ? (
            <p className="px-4 py-6 text-sm text-[var(--muted)]">Sign in to get notified when your results are ready.</p>
          ) : items.length === 0 ? (
            <p className="px-4 py-6 text-sm text-[var(--muted)]">
              Nothing yet. You&rsquo;ll be notified here when a session analysis, example video or practice feedback is ready.
            </p>
          ) : (
            <ul className="max-h-[420px] overflow-y-auto">
              {items.map((n) => {
                const failed = n.kind.endsWith("_failed");
                const Icon = failed ? CircleAlert : CircleCheck;
                return (
                  <li key={n.id}>
                    <button onClick={() => openItem(n)}
                      className="w-full text-left flex gap-3 px-4 py-3 transition-colors hover:bg-[var(--surface-2)]"
                      style={{ borderBottom: "1px solid var(--line-2)", background: n.read ? undefined : "var(--surface-2)" }}>
                      <Icon className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: failed ? "var(--bad)" : "var(--ok)" }} />
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-2">
                          <span className="text-sm text-[var(--ink)] truncate" style={{ fontWeight: n.read ? 400 : 600 }}>{n.title}</span>
                          {!n.read && <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "var(--accent-ink)" }} />}
                        </span>
                        {n.body && <span className="block text-xs text-[var(--ink-2)] mt-0.5 line-clamp-2">{n.body}</span>}
                        <span className="block text-[11px] text-[var(--faint)] mt-1">{ago(n.created_at)}</span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
