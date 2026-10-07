import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** A colour at a given opacity (2-digit hex alpha, e.g. "14" ≈ 8%). Works for hex colours
 *  and for theme variables like "var(--ok)", which can't take a hex alpha suffix. */
export function tint(color: string, alphaHex: string): string {
  if (!color.startsWith("var(")) return `${color}${alphaHex}`;
  const pct = Math.round((parseInt(alphaHex, 16) / 255) * 100);
  return `color-mix(in srgb, ${color} ${pct}%, transparent)`;
}

// Brand/series colours → a text colour that stays readable in both themes
const INK: Record<string, string> = {
  "#D6245F": "var(--pink-ink)", "#1A3A3A": "var(--accent-ink)", "#0A0A0A": "var(--accent-ink)",
  "#2F7A4F": "var(--ok)", "#A8620F": "var(--warn)", "#C2342C": "var(--bad)",
  "#6B4FC4": "var(--violet-ink)", "#1F6F6B": "var(--teal-ink)", "#3E6FB0": "var(--slate-ink)",
};

/** Use for TEXT drawn in a brand colour (fills keep the brand colour itself). */
export function inkOf(color: string): string;
export function inkOf(color: string | undefined): string | undefined;
export function inkOf(color: string | undefined) {
  return color ? INK[color.toUpperCase()] ?? color : color;
}
