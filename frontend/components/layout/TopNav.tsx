"use client";

// The app's only navigation: a floating clay bar (see .clay-nav in globals.css) with
// raised 3D tabs and a live 3D clay microphone as the logo. On small screens the
// links fold into a clay drop-down panel. It's the fixed anchor of page transitions.

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import dynamic from "next/dynamic";
import { Menu, Mic2, Settings, X } from "lucide-react";
import { useUserStore } from "@/store/useUserStore";
import { ThemeToggleButton } from "@/components/theme/ThemeToggle";
import NotificationBell from "@/components/layout/NotificationBell";

// The logo: the 3D clay mic from the home page, turning slowly (an icon until it loads)
const ClayScene = dynamic(() => import("@/components/three/ClayScene"), {
  ssr: false,
  loading: () => <Mic2 className="w-4 h-4 m-auto" style={{ color: "var(--pink)" }} />,
});

// The three practice functions, then progress and the reference matrix
const LINKS: { href: string; label: string; also?: string[] }[] = [
  { href: "/home", label: "Home" },
  { href: "/conversation", label: "Conversation" },
  { href: "/interview", label: "Interview" },
  { href: "/presentations", label: "Presentation" },
  { href: "/progress", label: "Progress", also: ["/results"] },
  { href: "/methodology", label: "How it's measured" },
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

  const isActive = (href: string) => {
    const paths = [href, ...(LINKS.find((l) => l.href === href)?.also ?? [])];
    return paths.some((p) => pathname === p || pathname.startsWith(p + "/"));
  };

  return (
    <header className="sticky top-0 z-50 px-2 sm:px-4 pt-2 sm:pt-3" style={{ viewTransitionName: "site-header" }}>
      <div className="clay-nav max-w-[1320px] mx-auto h-16 pl-2 pr-2 sm:pr-3 flex items-center gap-3 sm:gap-5 rounded-2xl">
        <Link href="/home" className="nav-logo flex items-center gap-2.5 flex-shrink-0" aria-label="SpeechMate home">
          <span className="clay w-11 h-11 rounded-lg relative overflow-hidden flex"
            style={{ background: "radial-gradient(90% 90% at 50% 35%, #FFE3CF, var(--peach))" }}>
            <ClayScene variant="logo" className="absolute inset-0" />
          </span>
          <span className="font-display text-[17px] text-[var(--ink)] hidden sm:inline">SpeechMate</span>
        </Link>
        <div className="-ml-2"><NotificationBell /></div>

        <nav className="hidden lg:flex items-center gap-1.5" aria-label="Main">
          {LINKS.map(({ href, label }) => {
            const active = isActive(href);
            return (
              <Link key={href} href={href} aria-current={active ? "page" : undefined}
                className={`nav-pill px-4 py-2 rounded-full text-sm font-medium ${active ? "nav-pill-active" : ""}`}>
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-1.5">
          <ThemeToggleButton />
          <Link href="/settings" aria-label="Settings"
            className="nav-pill w-9 h-9 rounded-full hidden sm:flex items-center justify-center"
            style={{ color: isActive("/settings") ? "var(--ink)" : "var(--muted)" }}>
            <Settings className="w-4 h-4" />
          </Link>
          <Link href="/profile" aria-label="Profile"
            className="clay w-9 h-9 rounded-full flex items-center justify-center text-white text-[11px] font-semibold transition-transform hover:-translate-y-0.5"
            style={{ background: "var(--accent)", outline: isActive("/profile") ? "2px solid var(--accent-ink)" : "none", outlineOffset: 2 }}>
            <span suppressHydrationWarning>{initials(user?.full_name)}</span>
          </Link>
          <button
            className="nav-pill lg:hidden w-10 h-10 rounded-full flex items-center justify-center text-[var(--ink)]"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            onClick={() => { setOpen((v) => !v); setOpenedAt(pathname); }}
          >
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {open && (
        <nav className="clay-nav lg:hidden max-w-[1320px] mx-auto mt-2 p-2 rounded-2xl flex flex-col gap-1" aria-label="Main">
          {[...LINKS, { href: "/settings", label: "Settings" }, { href: "/profile", label: "Profile" }].map(({ href, label }) => {
            const active = isActive(href);
            return (
              <Link key={href} href={href} aria-current={active ? "page" : undefined}
                className={`nav-pill px-4 py-3 rounded-xl text-sm font-medium ${active ? "nav-pill-active" : ""}`}>
                {label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
