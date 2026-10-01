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
  "#23345C": "var(--accent-ink)", "#17233E": "var(--accent-ink)",
  "#3F6B4C": "var(--ok)", "#4D7A59": "var(--ok)",
  "#8A5A22": "var(--warn)", "#9C6A28": "var(--warn)",
  "#8C3B32": "var(--bad)", "#9C4A40": "var(--bad)",
  "#5A5470": "var(--violet-ink)", "#79738C": "var(--violet-ink)", "#48435C": "var(--violet-ink)",
  "#3C6E78": "var(--teal-ink)", "#5C729B": "var(--slate-ink)",
};

/** Use for TEXT drawn in a brand colour (fills keep the brand colour itself). */
export function inkOf(color: string): string;
export function inkOf(color: string | undefined): string | undefined;
export function inkOf(color: string | undefined) {
  return color ? INK[color.toUpperCase()] ?? color : color;
}
