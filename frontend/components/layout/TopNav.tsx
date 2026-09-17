"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { Bell, Zap, Settings, FileText, Menu, X, User } from "lucide-react";

// The bottom liquid bar already covers Home / Practice / Analytics /
// Progress / Coach at every screen size — this "More" menu is only the
// pages that don't fit in its five tabs.
const MORE_LINKS = [
  { href: "/reports",    label: "Reports",   icon: FileText },
  { href: "/settings",   label: "Settings",  icon: Settings },
];

// Real liquid-glass distortion, not just a blur — an SVG filter warps what's
// behind the bar (feTurbulence → feDisplacementMap), then backdrop-filter
// chains that with blur + saturation so the warp still reads as frosted
// glass rather than a broken image. The turbulence seed drifts slowly via
// SMIL so the warp has a faint living quality instead of sitting frozen.
function LiquidGlassDefs() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden>
      <filter id="nav-liquid-glass" colorInterpolationFilters="sRGB">
        <feTurbulence type="fractalNoise" baseFrequency="0.010 0.018" numOctaves="2" seed="4" result="noise">
          <animate attributeName="baseFrequency" dur="22s" values="0.010 0.018;0.014 0.012;0.010 0.018" repeatCount="indefinite" />
        </feTurbulence>
        <feGaussianBlur in="noise" stdDeviation="3" result="softNoise" />
        <feDisplacementMap in="SourceGraphic" in2="softNoise" scale="22" xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </svg>
  );
}

export default function TopNav() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  // Close the mobile drawer whenever navigation happens.
  useEffect(() => { setMenuOpen(false); }, [pathname]);

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  return (
    <header className="sticky top-0 z-50 relative">
      <LiquidGlassDefs />

      {/* Distorted glass layer — sits behind the crisp content below it.
          backdrop-filter only warps what's BEHIND this element, so the
          logo/links/text drawn as normal children stay perfectly sharp. */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "rgba(255,255,255,0.5)",
          backdropFilter: "url(#nav-liquid-glass) blur(16px) saturate(1.8)",
          WebkitBackdropFilter: "blur(16px) saturate(1.8)",
          borderBottom: "1px solid rgba(255,255,255,0.5)",
        }}
      />
      {/* Specular sheen along the top edge — light catching the glass */}
      <div
        className="absolute inset-x-0 top-0 h-6 pointer-events-none"
        style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.55), transparent)" }}
      />
      <div className="absolute inset-x-0 bottom-0 h-px pointer-events-none" style={{ background: "#E6E2D8" }} />

      <div className="relative h-[60px] flex items-center justify-between px-4 sm:px-6 lg:px-8 gap-3">
        {/* ── Logo ──────────────────────────────────────────────────────── */}
        <Link href="/home" className="flex items-center gap-2.5 flex-shrink-0">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: "#23345C" }}
          >
            <Zap className="w-3.5 h-3.5 text-white" strokeWidth={2.5} />
          </div>
          <span className="font-bold text-[15px] tracking-tight whitespace-nowrap" style={{ color: "#17181C" }}>
            SpeechMate
          </span>
        </Link>

        {/* Primary navigation now lives in the liquid bar docked at the
            bottom of the viewport, at every screen size — this bar is just
            branding + utilities. The "More" toggle below reaches the pages
            that don't fit in the bottom bar's five tabs (Reports, Settings,
            Profile). */}

        {/* ── Right actions ────────────────────────────────────────────── */}
        <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
          {/* Notifications */}
          <button
            suppressHydrationWarning
            className="relative w-8 h-8 hidden sm:flex items-center justify-center rounded-xl transition-all press-effect"
            style={{ color: "#9B988E" }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(255,255,255,0.6)";
              e.currentTarget.style.color = "#17181C";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
              e.currentTarget.style.color = "#9B988E";
            }}
          >
            <Bell className="w-4 h-4" />
            <motion.span
              className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full"
              style={{ background: "#23345C", boxShadow: "0 0 0 2px #FFFFFF" }}
              animate={{ scale: [1, 1.4, 1] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            />
          </button>

          {/* Avatar */}
          <Link
            href="/profile"
            className="w-7 h-7 rounded-full flex items-center justify-center text-white text-[11px] font-bold cursor-pointer flex-shrink-0 press-effect"
            style={{
              background: "#23345C",
              boxShadow: isActive("/profile") ? "0 0 0 2px rgba(35,52,92,0.45)" : "0 0 0 2px rgba(35,52,92,0.18)",
            }}
          >
            SM
          </Link>

          {/* Mobile menu toggle */}
          <button
            aria-label={menuOpen ? "Close more menu" : "Open more menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((v) => !v)}
            className="w-8 h-8 flex items-center justify-center rounded-xl transition-all flex-shrink-0 press-effect"
            style={{ color: "#34343A", background: menuOpen ? "rgba(255,255,255,0.6)" : "transparent" }}
          >
            <motion.span
              key={menuOpen ? "close" : "open"}
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              transition={{ type: "spring", stiffness: 500, damping: 28 }}
              className="flex"
            >
              {menuOpen ? <X className="w-4.5 h-4.5" /> : <Menu className="w-4.5 h-4.5" />}
            </motion.span>
          </button>
        </div>
      </div>

      {/* ── "More" drawer — the pages the bottom bar's five tabs don't cover ── */}
      <motion.div
        className="overflow-hidden relative"
        initial={false}
        animate={{ height: menuOpen ? "auto" : 0 }}
        transition={{ type: "spring", stiffness: 420, damping: 38 }}
        style={{
          borderTop: menuOpen ? "1px solid rgba(255,255,255,0.5)" : "1px solid transparent",
          background: "rgba(255,255,255,0.7)",
          backdropFilter: "blur(20px) saturate(1.6)",
          WebkitBackdropFilter: "blur(20px) saturate(1.6)",
        }}
      >
        <nav className="max-w-[1320px] mx-auto px-3 sm:px-6 lg:px-8 py-3 grid grid-cols-2 sm:grid-cols-4 gap-1.5">
          {[...MORE_LINKS, { href: "/profile", label: "Profile", icon: User }].map(({ href, label, icon: Icon }, i) => {
            const active = isActive(href);
            return (
              <motion.div
                key={href}
                initial={{ opacity: 0, y: -6 }}
                animate={menuOpen ? { opacity: 1, y: 0 } : { opacity: 0, y: -6 }}
                transition={{ delay: menuOpen ? i * 0.03 : 0, duration: 0.18 }}
              >
                <Link
                  href={href}
                  className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors press-effect"
                  style={
                    active
                      ? { background: "rgba(35,52,92,0.08)", color: "#23345C", border: "1px solid rgba(35,52,92,0.25)" }
                      : { color: "#4B4C52", border: "1px solid transparent" }
                  }
                >
                  <Icon className="w-4 h-4 flex-shrink-0" strokeWidth={active ? 2.5 : 2} />
                  {label}
                </Link>
              </motion.div>
            );
          })}
        </nav>
      </motion.div>
    </header>
  );
}
