"use client";

import { useSyncExternalStore } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { getThemePref, setThemePref, subscribeTheme, type ThemePref } from "@/lib/theme";

const OPTIONS: { value: ThemePref; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

function useThemePref(): ThemePref | null {
  return useSyncExternalStore(subscribeTheme, getThemePref, () => null);
}

/** Light / Dark / System segmented control (Settings page). */
export function ThemeSelector() {
  const pref = useThemePref();
  return (
    <div role="radiogroup" aria-label="Theme" className="inline-flex" style={{ border: "1px solid var(--line)" }}>
      {OPTIONS.map(({ value, label, icon: Icon }, i) => {
        const active = pref === value;
        return (
          <button
            key={value}
            role="radio"
            aria-checked={active}
            onClick={() => setThemePref(value)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors"
            style={{
              background: active ? "var(--accent)" : "var(--surface)",
              color: active ? "#FFFFFF" : "var(--ink-2)",
              borderLeft: i ? "1px solid var(--line)" : undefined,
            }}
          >
            <Icon className="w-3.5 h-3.5" /> {label}
          </button>
        );
      })}
    </div>
  );
}

/** Compact top-bar button: switches between light and dark. */
export function ThemeToggleButton() {
  const pref = useThemePref();
  const dark = pref === "dark" || (pref === "system" && typeof window !== "undefined"
    && window.matchMedia("(prefers-color-scheme: dark)").matches);
  return (
    <button
      onClick={() => setThemePref(dark ? "light" : "dark")}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      title={dark ? "Light mode" : "Dark mode"}
      className="w-9 h-9 flex items-center justify-center transition-colors hover:bg-[var(--surface-2)]"
      style={{ color: "var(--muted)" }}
    >
      <span suppressHydrationWarning>{pref === null ? <Moon className="w-4 h-4" /> : dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}</span>
    </button>
  );
}
