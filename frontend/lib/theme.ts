// Light / dark / system theme. The resolved theme is written to <html data-theme>,
// which switches the CSS colour variables in globals.css.

export type ThemePref = "light" | "dark" | "system";
const KEY = "speechmate-theme";
const listeners = new Set<() => void>();

export function getThemePref(): ThemePref {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

function resolve(pref: ThemePref): "light" | "dark" {
  if (pref !== "system") return pref;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(pref: ThemePref = getThemePref()) {
  document.documentElement.dataset.theme = resolve(pref);
}

export function setThemePref(pref: ThemePref) {
  try { localStorage.setItem(KEY, pref); } catch { /* private mode: still applies for this page */ }
  applyTheme(pref);
  listeners.forEach((l) => l());
}

/** For useSyncExternalStore: re-renders on a theme change here or in the OS (when "system"). */
export function subscribeTheme(onChange: () => void) {
  listeners.add(onChange);
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  const onSystem = () => { if (getThemePref() === "system") { applyTheme("system"); onChange(); } };
  mq.addEventListener("change", onSystem);
  return () => { listeners.delete(onChange); mq.removeEventListener("change", onSystem); };
}

// Text size: "large" scales every rem-based size by 112.5% (<html data-text="large">, globals.css)
export type TextSize = "normal" | "large";
const TEXT_KEY = "speechmate-text";

export function getTextSize(): TextSize {
  try { return localStorage.getItem(TEXT_KEY) === "large" ? "large" : "normal"; } catch { return "normal"; }
}

export function setTextSize(size: TextSize) {
  try { localStorage.setItem(TEXT_KEY, size); } catch { /* private mode: still applies for this page */ }
  document.documentElement.dataset.text = size;
  listeners.forEach((l) => l());
}

/** Inline <head> script: apply the saved theme and text size before first paint (no flash). */
export const THEME_BOOT_SCRIPT = `(function(){try{var p=localStorage.getItem("${KEY}");var d=p==="dark"||(p!=="light"&&matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.dataset.theme=d?"dark":"light";document.documentElement.dataset.text=localStorage.getItem("${TEXT_KEY}")==="large"?"large":"normal";}catch(e){}})();`;
