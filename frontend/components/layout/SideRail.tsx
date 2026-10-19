"use client";

// The second navigation: a slim rail on the left for tools and your account, kept apart from
// the top bar (where you practise). Three floating groups: the theme, your pages, sign out.
// Desktop only; on smaller screens the top bar's menu has the same links.

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, LogOut, Moon, Settings, ShieldCheck, Sun, UserRound, type LucideIcon } from "lucide-react";
import { getThemePref, setThemePref, subscribeTheme } from "@/lib/theme";
import { useAuth } from "@/hooks/useAuth";

const PAGES: { href: string; label: string; icon: LucideIcon }[] = [
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/settings#privacy", label: "Your data & privacy", icon: ShieldCheck },
  { href: "/methodology", label: "How it's measured", icon: BookOpen },
];

const isDark = () => {
  const pref = getThemePref();
  return pref === "dark" || (pref === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
};

/** A round rail button with its name shown beside it on hover and keyboard focus. */
function RailItem({ label, active, children }: { label: string; active?: boolean; children: (cls: string) => React.ReactNode }) {
  return (
    <li className="relative group">
      {children(`nav-pill w-10 h-10 rounded-full flex items-center justify-center ${active ? "nav-pill-active" : ""}`)}
      <span role="tooltip" className="pointer-events-none absolute left-full top-1/2 -translate-y-1/2 ml-3 px-2.5 py-1 rounded-md text-xs font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity"
        style={{ background: "var(--ink)", color: "var(--surface)" }}>
        {label}
      </span>
    </li>
  );
}

export default function SideRail() {
  const pathname = usePathname();
  const { logout } = useAuth();
  // null while rendering on the server: neither theme button shows as selected yet
  const dark = useSyncExternalStore(subscribeTheme, isDark, () => null);
  const group = "clay-nav rounded-full p-1.5 flex flex-col gap-1.5";

  return (
    <aside aria-label="Tools and account"
      className="hidden lg:flex fixed left-4 top-24 bottom-6 z-40 flex-col justify-between">
      <div className="flex flex-col gap-6">
        <ul className={group} aria-label="Theme">
          {([["Light mode", Sun, false], ["Dark mode", Moon, true]] as const).map(([label, Icon, wantDark]) => (
            <RailItem key={label} label={label} active={dark === wantDark}>
              {(cls) => (
                <button className={cls} aria-label={label} aria-pressed={dark === wantDark}
                  onClick={() => setThemePref(wantDark ? "dark" : "light")}>
                  <Icon className="w-[18px] h-[18px]" />
                </button>
              )}
            </RailItem>
          ))}
        </ul>

        <ul className={group} aria-label="Your pages">
          {PAGES.map(({ href, label, icon: Icon }) => {
            // "Your data" is a section of Settings, so only the Settings button lights up there
            const active = !href.includes("#") && (pathname === href || pathname.startsWith(href + "/"));
            return (
              <RailItem key={href} label={label} active={active}>
                {(cls) => (
                  <Link href={href} className={cls} aria-label={label} aria-current={active ? "page" : undefined}>
                    <Icon className="w-[18px] h-[18px]" />
                  </Link>
                )}
              </RailItem>
            );
          })}
        </ul>
      </div>

      <ul className={group} aria-label="Session">
        <RailItem label="Sign out">
          {(cls) => (
            <button className={cls} aria-label="Sign out" onClick={() => logout()}>
              <LogOut className="w-[18px] h-[18px]" />
            </button>
          )}
        </RailItem>
      </ul>
    </aside>
  );
}
