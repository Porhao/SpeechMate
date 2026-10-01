"use client";

// The app's only navigation: one slim, solid top bar. Text links with an
// underline for the current page; on small screens they fold into a plain list.

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, Mic2, Settings, X } from "lucide-react";
import { useUserStore } from "@/store/useUserStore";
import { ThemeToggleButton } from "@/components/theme/ThemeToggle";
import NotificationBell from "@/components/layout/NotificationBell";

const LINKS = [
  { href: "/home", label: "Home" },
  { href: "/practice", label: "Practice" },
  { href: "/presentations", label: "Presentations" },
  { href: "/coach", label: "Coach" },
  { href: "/progress", label: "Progress" },
  { href: "/dashboard", label: "Analytics" },
  { href: "/reports", label: "Reports" },
  { href: "/methodology", label: "Reference" },
];

function initials(name: string | undefined) {
  if (!name) return "·";
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join("");
}

export default function TopNav() {
  const pathname = usePathname();
  const user = useUserStore((s) => s.user);
  const [open, setOpen] = useState(false);
  const [openedAt, setOpenedAt] = useState(pathname);
  // Close the mobile menu after navigating (derived during render, no effect needed)
  if (open && openedAt !== pathname) setOpen(false);

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/");

  return (
    <header className="sticky top-0 z-50 bg-[var(--surface)]" style={{ borderBottom: "1px solid var(--line)" }}>
      <div className="max-w-[1320px] mx-auto h-14 px-4 sm:px-6 flex items-center gap-8">
        <Link href="/home" className="flex items-center gap-2 flex-shrink-0">
          <span className="w-7 h-7 flex items-center justify-center" style={{ background: "var(--accent)" }}>
            <Mic2 className="w-3.5 h-3.5 text-white" />
          </span>
          <span className="font-semibold text-[15px] tracking-tight text-[var(--ink)]">SpeechMate</span>
        </Link>
        {/* Notifications sit at the top left, next to the wordmark */}
        <div className="-ml-5"><NotificationBell /></div>

        <nav className="hidden lg:flex items-stretch h-full gap-6" aria-label="Main">
          {LINKS.map(({ href, label }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className="relative flex items-center text-sm transition-colors"
                style={{ color: active ? "var(--ink)" : "var(--muted)", fontWeight: active ? 600 : 400 }}
              >
                {label}
                {active && <span className="absolute left-0 right-0 bottom-0 h-[2px]" style={{ background: "var(--accent)" }} />}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-1">
          <ThemeToggleButton />
          <Link
            href="/settings"
            aria-label="Settings"
            className="w-9 h-9 hidden sm:flex items-center justify-center transition-colors hover:bg-[var(--surface-2)]"
            style={{ color: isActive("/settings") ? "var(--ink)" : "var(--muted)" }}
          >
            <Settings className="w-4 h-4" />
          </Link>
          <Link
            href="/profile"
            aria-label="Profile"
            className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-semibold"
            style={{ background: "var(--accent)", outline: isActive("/profile") ? "2px solid #23345C55" : "none", outlineOffset: 2 }}
          >
            <span suppressHydrationWarning>{initials(user?.full_name)}</span>
          </Link>
          <button
            className="lg:hidden w-9 h-9 flex items-center justify-center text-[var(--ink)] hover:bg-[var(--surface-2)]"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            onClick={() => { setOpen((v) => !v); setOpenedAt(pathname); }}
          >
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {open && (
        <nav className="lg:hidden bg-[var(--surface)]" style={{ borderTop: "1px solid var(--line)" }} aria-label="Main">
          {[...LINKS, { href: "/settings", label: "Settings" }, { href: "/profile", label: "Profile" }].map(({ href, label }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                className="block px-5 py-3 text-sm"
                style={{
                  color: active ? "var(--ink)" : "var(--ink-2)",
                  fontWeight: active ? 600 : 400,
                  borderLeft: `3px solid ${active ? "#23345C" : "transparent"}`,
                  borderBottom: "1px solid var(--line-2)",
                }}
              >
                {label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
