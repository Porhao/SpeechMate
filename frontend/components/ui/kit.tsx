"use client";

// Small shared building blocks for the app pages: plain, square-cornered and
// theme-aware (everything reads the CSS colour tokens, so dark mode just works).

import Link from "next/link";
import type { ButtonHTMLAttributes, CSSProperties, PointerEvent, ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { MetricStatus } from "@/types";

export function PageHeader({ eyebrow, title, children, art }: { eyebrow?: string; title: string; children?: ReactNode; art?: ReactNode }) {
  const text = (
    <div>
      {eyebrow && <p className="text-xs font-semibold uppercase tracking-[0.12em] mb-3" style={{ color: "var(--muted)" }}>{eyebrow}</p>}
      <h1 className="font-display text-4xl sm:text-5xl leading-[1.05]" style={{ color: "var(--ink)" }}>{title}</h1>
      {children && <div className="mt-4 text-base max-w-2xl leading-relaxed" style={{ color: "var(--ink-2)" }}>{children}</div>}
    </div>
  );
  // With `art` (e.g. a 3D ClayArt), the text sits left and the art right on wide screens
  return art
    ? <div className="mb-10 grid lg:grid-cols-[1fr_380px] gap-6 items-center">{text}{art}</div>
    : <div className="mb-10">{text}</div>;
}

export function Card({ children, className, title, action }: { children: ReactNode; className?: string; title?: string; action?: ReactNode }) {
  return (
    <section className={cn("p-6 rounded-lg", className)} style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow-card)" }}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-3 mb-4">
          {title && <h2 className="text-sm font-semibold" style={{ color: "var(--ink)" }}>{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

type Variant = "primary" | "secondary" | "ghost";
const VARIANT: Record<Variant, React.CSSProperties> = {
  primary: { background: "var(--accent)", color: "#fff", border: "1px solid var(--accent)" },
  secondary: { background: "var(--surface)", color: "var(--ink)", border: "1px solid var(--line-strong)" },
  ghost: { background: "transparent", color: "var(--accent-ink)", border: "1px solid transparent" },
};
const BTN = "inline-flex items-center justify-center gap-2 h-11 px-5 rounded-md text-sm font-semibold transition-opacity hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed";

export function Button({ variant = "primary", className, style, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button className={cn(BTN, className)} style={{ ...VARIANT[variant], ...style }} {...rest} />;
}

export function LinkButton({ href, variant = "primary", className, children }: { href: string; variant?: Variant; className?: string; children: ReactNode }) {
  return <Link href={href} className={cn(BTN, className)} style={VARIANT[variant]}>{children}</Link>;
}

/** A link card that leans towards the pointer in 3D (see .tilt in globals.css). Mouse/pen only. */
export function TiltCard({ href, className, style, children }: { href: string; className?: string; style?: CSSProperties; children: ReactNode }) {
  const set = (el: HTMLElement, rx: number, ry: number, lift: number) => {
    el.style.setProperty("--rx", `${rx}deg`); el.style.setProperty("--ry", `${ry}deg`); el.style.setProperty("--lift", `${lift}px`);
  };
  const onMove = (e: PointerEvent<HTMLAnchorElement>) => {
    if (e.pointerType === "touch") return;
    const r = e.currentTarget.getBoundingClientRect();
    set(e.currentTarget, -((e.clientY - r.top) / r.height - 0.5) * 10, ((e.clientX - r.left) / r.width - 0.5) * 12, -6);
  };
  return (
    <Link href={href} className={cn("tilt clay no-press", className)} style={style}
      onPointerMove={onMove} onPointerLeave={(e) => set(e.currentTarget, 0, 0, 0)}>
      {children}
    </Link>
  );
}

export function Field({ label, hint, optional, children }: { label: string; hint?: string; optional?: boolean; children: ReactNode }) {
  return (
    <label className="block">
      <span className="flex items-baseline gap-2 text-sm font-medium mb-1.5" style={{ color: "var(--ink)" }}>
        {label}{optional && <span className="text-xs font-normal" style={{ color: "var(--muted)" }}>optional</span>}
      </span>
      {children}
      {hint && <span className="block text-xs mt-1" style={{ color: "var(--muted)" }}>{hint}</span>}
    </label>
  );
}

export const inputClass = "w-full px-4 py-3 rounded-md text-sm outline-none focus:border-[var(--ink)]! focus:ring-2 focus:ring-[var(--accent-ink)]/20";
export const inputStyle: React.CSSProperties = { background: "var(--surface)", color: "var(--ink)", border: "1px solid var(--line-strong)" };

const STATUS_COLOR: Record<Exclude<MetricStatus, null>, string> = { good: "var(--ok)", ok: "var(--warn)", work: "var(--bad)" };
const STATUS_LABEL: Record<Exclude<MetricStatus, null>, string> = { good: "Strong", ok: "Okay", work: "Work on this" };

export function statusColor(status: MetricStatus) {
  return status ? STATUS_COLOR[status] : "var(--faint)";
}

export function StatusBadge({ status }: { status: MetricStatus }) {
  if (!status) return <span className="text-xs" style={{ color: "var(--faint)" }}>Not measured</span>;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-semibold" style={{ color: STATUS_COLOR[status] }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: STATUS_COLOR[status] }} />
      {STATUS_LABEL[status]}
    </span>
  );
}

export function ScoreBar({ score, status }: { score: number | null; status: MetricStatus }) {
  return (
    <div className="h-1.5 w-full rounded-full overflow-hidden" style={{ background: "var(--line-2)" }} aria-hidden>
      {score != null && <div className="h-full rounded-full" style={{ width: `${Math.max(3, score)}%`, background: statusColor(status) }} />}
    </div>
  );
}

export function Dots({ value, max = 5, label }: { value: number; max?: number; label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs" style={{ color: "var(--ink-2)" }}>
      {label}
      <span className="inline-flex gap-0.5" aria-label={`${value} out of ${max}`}>
        {Array.from({ length: max }, (_, i) => (
          <span key={i} className="w-2 h-2 rounded-full" style={{ background: i < value ? "var(--accent-ink)" : "var(--line)" }} />
        ))}
      </span>
    </span>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warn" | "bad"; children: ReactNode }) {
  const c = tone === "warn" ? "var(--warn)" : tone === "bad" ? "var(--bad)" : "var(--accent-ink)";
  return (
    <div className="px-4 py-3 rounded-md text-sm leading-relaxed" style={{ borderLeft: `3px solid ${c}`, background: "var(--surface-2)", color: "var(--ink-2)" }}>
      {children}
    </div>
  );
}
