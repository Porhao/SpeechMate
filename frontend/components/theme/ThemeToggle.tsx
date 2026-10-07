"use client";

import { useSyncExternalStore } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { getTextSize, getThemePref, setTextSize, setThemePref, subscribeTheme, type TextSize, type ThemePref } from "@/lib/theme";

const OPTIONS: { value: ThemePref; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

function useThemePref(): ThemePref | null {
  return useSyncExternalStore(subscribeTheme, getThemePref, () => null);
}

/** Normal / Large text segmented control (Settings page). */
export function TextSizeSelector() {
  const size = useSyncExternalStore(subscribeTheme, getTextSize, () => null);
  return (
    <div role="radiogroup" aria-label="Text size" className="inline-flex p-1 gap-1 rounded-full" style={{ background: "var(--surface-3)" }}>
      {([["normal", "Normal"], ["large", "Large"]] as [TextSize, string][]).map(([value, label]) => {
        const active = size === value;
        return (
          <button key={value} role="radio" aria-checked={active} onClick={() => setTextSize(value)}
            className="px-3.5 py-1.5 rounded-full font-medium transition-colors"
            style={{ background: active ? "var(--accent)" : "transparent", color: active ? "#FFFFFF" : "var(--ink-2)", fontSize: value === "large" ? 15 : 12 }}>
            {label}
          </button>
        );
      })}
    </div>
  );
}

/** Light / Dark / System segmented control (Settings page). */
export function ThemeSelector() {
  const pref = useThemePref();
  return (
    <div role="radiogroup" aria-label="Theme" className="inline-flex p-1 gap-1 rounded-full" style={{ background: "var(--surface-3)" }}>
      {OPTIONS.map(({ value, label, icon: Icon }) => {
        const active = pref === value;
        return (
          <button
            key={value}
            role="radio"
            aria-checked={active}
            onClick={() => setThemePref(value)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
            style={{
              background: active ? "var(--accent)" : "transparent",
              color: active ? "#FFFFFF" : "var(--ink-2)",
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
      className="w-9 h-9 rounded-full flex items-center justify-center transition-colors hover:bg-[var(--surface-3)]"
      style={{ color: "var(--muted)" }}
    >
      <span suppressHydrationWarning>{pref === null ? <Moon className="w-4 h-4" /> : dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}</span>
    </button>
  );
}
