"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Mic2, MessageSquare, ClipboardList,
  TrendingUp, FileText, User, Settings, Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { label: "Dashboard",   href: "/dashboard",  icon: LayoutDashboard },
  { label: "Practice",    href: "/practice",   icon: Mic2 },
  { label: "AI Coach",    href: "/coach",      icon: MessageSquare },
  { label: "Assessments", href: "/assessment", icon: ClipboardList },
  { label: "Progress",    href: "/progress",   icon: TrendingUp },
  { label: "Reports",     href: "/reports",    icon: FileText },
];

const bottomItems = [
  { label: "Profile",  href: "/profile",  icon: User },
  { label: "Settings", href: "/settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="w-[280px] h-screen fixed left-0 top-0 flex flex-col z-40"
      style={{
        background: "rgba(6,9,24,0.85)",
        backdropFilter: "blur(24px) saturate(1.5)",
        WebkitBackdropFilter: "blur(24px) saturate(1.5)",
        borderRight: "1px solid rgba(255,255,255,0.07)",
      }}
    >
      {/* Logo */}
      <div className="px-6 py-5" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <Link href="/dashboard" className="flex items-center gap-3 group">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center btn-glow"
            style={{
              background: "linear-gradient(135deg, #5A5470, #403C54)",
            }}
          >
            <Zap className="w-4.5 h-4.5 text-white" strokeWidth={2.5} />
          </div>
          <div>
            <span className="gradient-text font-bold text-[17px] tracking-tight block leading-none">
              SpeechMate
            </span>
            <span className="text-[10px] text-white/30 font-medium tracking-widest uppercase">
              AI Coach
            </span>
          </div>
        </Link>
      </div>

      {/* Main Nav */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        <p className="text-[10px] font-semibold text-white/25 uppercase tracking-widest px-3 mb-3">
          Navigation
        </p>
        <ul className="space-y-0.5">
          {navItems.map((item) => {
            const Icon   = item.icon;
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 press-effect",
                    active
                      ? "text-white"
                      : "text-white/45 hover:text-white/80 hover:bg-white/5",
                  )}
                  style={active ? {
                    background: "linear-gradient(135deg, rgba(90,84,112,0.28), rgba(109,40,217,0.16))",
                    boxShadow: "inset 0 0 0 1px rgba(121,115,140,0.25), 0 0 16px rgba(90,84,112,0.12)",
                  } : {}}
                >
                  {/* Active left border accent */}
                  {active && (
                    <span
                      className="absolute left-0 w-0.5 h-6 rounded-full"
                      style={{ background: "linear-gradient(180deg, #5C729B, #79738C)" }}
                    />
                  )}
                  <Icon
                    className={cn("w-4.5 h-4.5 shrink-0 transition-all", active ? "text-violet-300" : "text-white/30")}
                    strokeWidth={active ? 2.5 : 2}
                  />
                  {item.label}
                  {active && (
                    <span className="ml-auto w-1.5 h-1.5 rounded-full bg-violet-400" />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Bottom Nav */}
      <div className="px-3 py-4" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
        <ul className="space-y-0.5">
          {bottomItems.map((item) => {
            const Icon   = item.icon;
            const active = pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 press-effect",
                    active ? "text-white" : "text-white/45 hover:text-white/80 hover:bg-white/5",
                  )}
                  style={active ? {
                    background: "rgba(90,84,112,0.2)",
                    boxShadow: "inset 0 0 0 1px rgba(121,115,140,0.25)",
                  } : {}}
                >
                  <Icon
                    className={cn("w-4.5 h-4.5 shrink-0", active ? "text-violet-300" : "text-white/30")}
                    strokeWidth={active ? 2.5 : 2}
                  />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* User tag at bottom */}
        <div
          className="mt-4 px-3 py-3 rounded-xl flex items-center gap-3"
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-white"
            style={{ background: "linear-gradient(135deg, #5C729B, #79738C)" }}
          >
            S
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-white/80 truncate">SpeechMate User</p>
            <p className="text-[10px] text-white/30">Free Plan</p>
          </div>
          <div className="w-2 h-2 rounded-full bg-[#4D7A59] shadow-[0_0_6px_rgba(77,122,89,0.6)]" />
        </div>
      </div>
    </aside>
  );
}
