"use client";

/* ==========================================================================
   Liquid bottom navigation — ported from a reference vanilla-JS build
   ("Meniscus") the geometry and physics come from directly. Same three
   moving parts:

     1. measure()  derives every dimension from the bar's actual measured
                    box and writes it back, so the path and the DOM never
                    disagree about where the bead sits.
     2. buildPath() the bar's outline as ONE path whose notch is parametric
                    — centre, shoulder radii, bowl radius — solved from
                    tangency, not assembled from eyeballed curves. Because
                    it's computed, the notch can lean into the direction of
                    travel and shallow out at speed.
     3. loop()      one rAF, one spring, fixed 1/240s substeps for stability.
                    The bead's own velocity drives the lean and the squash;
                    the loop stops itself once settled.

   Recoloured for this app's warm ink-on-paper palette (the reference is a
   dark obsidian-plate theme) — the rim that traces the meniscus curve is a
   hairline border instead of a glow, matching every other card in the app.
   Tab list follows the APG pattern: roving tabindex, arrow/Home/End keys.
   ========================================================================== */

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, Mic2, TrendingUp, ClipboardList, MessageSquare, type LucideIcon } from "lucide-react";

const TABS: { href: string; label: string; icon: LucideIcon; acc: string }[] = [
  { href: "/home",      label: "Home",      icon: LayoutDashboard, acc: "#23345C" },
  { href: "/practice",  label: "Practice",  icon: Mic2,            acc: "#5A5470" },
  { href: "/dashboard", label: "Analytics", icon: TrendingUp,      acc: "#8A5A22" },
  { href: "/progress",  label: "Progress",  icon: ClipboardList,   acc: "#3F6B4C" },
  { href: "/coach",     label: "Coach",     icon: MessageSquare,   acc: "#3C6E78" },
];

const clamp = (v: number, a: number, b: number) => (v < a ? a : v > b ? b : v);
const smooth = (t: number) => { const x = clamp(t, 0, 1); return x * x * (3 - 2 * x); };

const hexToRgb = (hex: string): [number, number, number] => {
  const h = hex.replace("#", "");
  const n = parseInt(h, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};
const ACC = TABS.map((t) => hexToRgb(t.acc));
const mixRGB = (a: [number, number, number], b: [number, number, number], t: number) =>
  `${Math.round(a[0] + (b[0] - a[0]) * t)} ${Math.round(a[1] + (b[1] - a[1]) * t)} ${Math.round(a[2] + (b[2] - a[2]) * t)}`;

// ── Geometry ──────────────────────────────────────────────────────────────────
// Half-width of a trough built from a shoulder of radius s (centred at
// y = s, tangent to the flat top edge) and a bowl of radius rb (centred at
// y = by). Falls straight out of external tangency: |centre1–centre2| = s+rb.
function reach(s: number, rb: number, by: number) {
  return Math.sqrt(Math.max((s + rb) ** 2 - (s - by) ** 2, 1));
}

// One closed outline: rounded corners all round, a flat run along the top
// interrupted by the socket — convex shoulder, concave bowl, convex shoulder.
// The bowl's sweep/large-arc flags are solved from the actual tangent-point
// angles rather than assumed, so asymmetric shoulders never mis-draw.
function buildPath(bx: number, by: number, rb: number, sL: number, sR: number, W: number, H: number, R: number) {
  const wing = (s: number, side: 1 | -1) => {
    const L = s + rb;
    const half = reach(s, rb, by);
    const sx = bx + side * half;
    return { sx, tx: sx + ((bx - sx) / L) * s, ty: s + ((by - s) / L) * s };
  };
  const A = wing(sL, -1), B = wing(sR, 1);

  const a0 = Math.atan2(A.ty - by, A.tx - bx);
  const a1 = Math.atan2(B.ty - by, B.tx - bx);
  let sweep = ((a0 - a1) * 180) / Math.PI;
  while (sweep < 0) sweep += 360;
  const large = sweep > 180 ? 1 : 0;

  const n = (v: number) => v.toFixed(2);
  return (
    `M0 ${n(R)}` +
    `A${n(R)} ${n(R)} 0 0 1 ${n(R)} 0` +
    `L${n(clamp(A.sx, R, W - R))} 0` +
    `A${n(sL)} ${n(sL)} 0 0 1 ${n(A.tx)} ${n(A.ty)}` +
    `A${n(rb)} ${n(rb)} 0 ${large} 0 ${n(B.tx)} ${n(B.ty)}` +
    `A${n(sR)} ${n(sR)} 0 0 1 ${n(clamp(B.sx, R, W - R))} 0` +
    `L${n(W - R)} 0` +
    `A${n(R)} ${n(R)} 0 0 1 ${n(W)} ${n(R)}` +
    `L${n(W)} ${n(H - R)}` +
    `A${n(R)} ${n(R)} 0 0 1 ${n(W - R)} ${n(H)}` +
    `L${n(R)} ${n(H)}` +
    `A${n(R)} ${n(R)} 0 0 1 0 ${n(H - R)}` +
    `Z`
  );
}

// Geometry the bar carries — mirrors the reference's `G` object, but as a
// ref so React never re-renders for it.
interface Geo { W: number; H: number; R: number; D: number; RB: number; S: number; CY: number; slots: number[]; span: number }

const clientPx = (v: number) => Math.round(v);

export default function LiquidBottomNav() {
  const pathname = usePathname();
  const router = useRouter();
  const activeIndex = Math.max(0, TABS.findIndex((t) => pathname === t.href || pathname.startsWith(t.href + "/")));

  const dockRef  = useRef<HTMLDivElement>(null);
  const svgRef   = useRef<SVGSVGElement>(null);
  const fillRef  = useRef<SVGPathElement>(null);
  const beadRef  = useRef<HTMLDivElement>(null);
  const tabRefs  = useRef<(HTMLButtonElement | null)[]>([]);

  const [ready, setReady] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [current, setCurrent] = useState(activeIndex); // label pinned to this tab, roving tabindex lives here

  const geoRef = useRef<Geo>({ W: 0, H: 0, R: 17, D: 56, RB: 32, S: 12, CY: 0, slots: [], span: 80 });
  const xRef = useRef(0), vRef = useRef(0), targetRef = useRef(0);
  const rafRef = useRef<number>(0), lastRef = useRef(0);
  const draggingRef = useRef(false);
  const runningRef = useRef(false);
  const startXRef = useRef(0), pidRef = useRef<number | null>(null), suppressClickRef = useRef(false);

  // ── measure() — derive geometry from the bar's own measured box ──────────
  const measure = useCallback((): boolean => {
    const dock = dockRef.current;
    if (!dock) return false;
    const r = dock.getBoundingClientRect();
    const W = clientPx(r.width), H = clientPx(r.height);
    if (W < 40 || H < 30) return false;

    const slots = tabRefs.current.map((el) => {
      if (!el) return 0;
      const b = el.getBoundingClientRect();
      return b.left - r.left + b.width / 2;
    });
    const span = slots.length > 1 ? slots[1] - slots[0] : W;

    const G = geoRef.current;
    G.W = W; G.H = H; G.slots = slots; G.span = span;
    G.R = clamp(H * 0.28, 16, 26);
    G.CY = 0; // the bead rides on the surface line, never lifts off

    // The outer shoulder has to clear the bar's own corner — shrink the
    // bead proportionally until the first tab's trough fits.
    let D = Math.min(H * 0.62, span * 0.62);
    const room = slots[0] - G.R - 5;
    for (let i = 0; i < 4 && room > 4; i++) {
      const hw = reach(D * 0.22, D / 2 + 4, G.CY);
      if (hw <= room) break;
      D *= room / hw;
    }
    G.D = Math.max(Math.round(D), 30);
    G.S = G.D * 0.22;
    G.RB = G.D / 2 + 4;

    svgRef.current?.setAttribute("viewBox", `0 0 ${W} ${H}`);
    dock.style.setProperty("--rise", `${(H / 2 - G.CY).toFixed(1)}px`);
    return true;
  }, []);

  // ── paint() — one physics frame written straight to the DOM ──────────────
  const paint = useCallback((x: number, v: number) => {
    const G = geoRef.current;
    if (!G.W || !G.D) return;

    // q: signed travel, −1…1. Everything liquid is a function of it. Halved
    // while dragging, since raw pointer deltas spike higher than the spring
    // ever would settling on its own.
    const q = clamp(v / 1100, -1, 1) * (draggingRef.current ? 0.5 : 1);
    const mag = Math.abs(q);

    // Trailing shoulder draws out long, leading tightens, both widen a
    // little with speed — the socket smears behind the weight in it.
    const sL = clamp(G.S * (1 + 0.06 * mag + 0.4 * q), G.S * 0.55, G.S * 2.1);
    const sR = clamp(G.S * (1 + 0.06 * mag - 0.4 * q), G.S * 0.55, G.S * 2.1);

    const bx = clamp(x, G.slots[0] ?? 0, G.slots[G.slots.length - 1] ?? G.W);
    if (fillRef.current) {
      fillRef.current.setAttribute("d", buildPath(bx, G.CY, G.RB, sL, sR, G.W, G.H, G.R));
    }

    // Volume-preserving squash along the direction of travel.
    if (beadRef.current) {
      const sx = 1 + 0.07 * mag;
      beadRef.current.style.width = `${G.D}px`;
      beadRef.current.style.height = `${G.D}px`;
      beadRef.current.style.transform =
        `translate3d(${(bx - G.D / 2).toFixed(2)}px, ${(G.CY - G.D / 2).toFixed(2)}px, 0) scale(${sx.toFixed(3)}, ${(1 / sx).toFixed(3)})`;
    }

    // Icons rise into the bead as it sweeps past; the accent is whatever
    // tab is actually under the bead right now, blended toward whichever
    // neighbour it's leaning on.
    let near = 0, nd = Infinity;
    G.slots.forEach((cx, i) => {
      const dx = Math.abs(bx - cx);
      if (dx < nd) { nd = dx; near = i; }
      tabRefs.current[i]?.style.setProperty("--t", smooth(clamp(1 - dx / (G.span * 0.55), 0, 1)).toFixed(3));
    });
    const side = bx >= G.slots[near] ? 1 : -1;
    const other = clamp(near + side, 0, TABS.length - 1);
    const t = other === near ? 0 : clamp(Math.abs(bx - G.slots[near]) / G.span, 0, 1);
    dockRef.current?.style.setProperty("--glow-rgb", mixRGB(ACC[near], ACC[other], t));

    if (!draggingRef.current) setCurrent((c) => (c === near ? c : near));
  }, []);

  // ── loop() — fixed-substep spring, self-starting / self-stopping ─────────
  const loop = useCallback((now: number) => {
    rafRef.current = 0;
    const dt = Math.min((now - (lastRef.current || now)) / 1000, 1 / 30);
    lastRef.current = now;

    const K = draggingRef.current ? 900 : 142;
    const C = draggingRef.current ? 52 : 19.3;
    let x = xRef.current, v = vRef.current;
    const target = targetRef.current;
    let step = dt;
    while (step > 0) {
      const h = Math.min(step, 1 / 240);
      v += (-K * (x - target) - C * v) * h;
      x += v * h;
      step -= h;
    }
    xRef.current = x; vRef.current = v;
    paint(x, v);

    if (Math.abs(x - target) > 0.05 || Math.abs(v) > 0.6 || draggingRef.current) {
      rafRef.current = requestAnimationFrame(loop);
    } else {
      xRef.current = target; vRef.current = 0; paint(target, 0);
      runningRef.current = false;
    }
  }, [paint]);

  const run = useCallback(() => {
    if (runningRef.current) return;
    runningRef.current = true;
    lastRef.current = 0;
    rafRef.current = requestAnimationFrame(loop);
  }, [loop]);

  const reducedMotion = () =>
    typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  const jump = useCallback((to: number) => {
    targetRef.current = to;
    if (reducedMotion() && !draggingRef.current) { xRef.current = to; vRef.current = 0; paint(to, 0); return; }
    run();
  }, [paint, run]);

  // ── layout — measure on mount, on resize, and once fonts settle ──────────
  const layout = useCallback((animate: boolean) => {
    if (!measure()) return;
    const G = geoRef.current;
    const to = G.slots[current] ?? 0;
    if (animate) jump(to);
    else { xRef.current = targetRef.current = to; vRef.current = 0; paint(to, 0); }
    setReady(true);
  }, [measure, current, jump, paint]);

  useLayoutEffect(() => {
    layout(false);
    const ro = new ResizeObserver(() => layout(false));
    if (dockRef.current) ro.observe(dockRef.current);
    document.fonts?.ready.then(() => layout(false)).catch(() => {});
    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => () => cancelAnimationFrame(rafRef.current), []);

  // Route changed elsewhere (or on mount) — follow it, unless mid-drag.
  useEffect(() => {
    if (draggingRef.current) return;
    setCurrent(activeIndex);
    const to = geoRef.current.slots[activeIndex];
    if (to !== undefined) jump(to);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeIndex]);

  // ── selection ──────────────────────────────────────────────────────────
  const select = useCallback((i: number, opts?: { focus?: boolean }) => {
    const idx = (i + TABS.length) % TABS.length;
    setCurrent(idx);
    jump(geoRef.current.slots[idx]);
    if (opts?.focus) tabRefs.current[idx]?.focus();
    if (TABS[idx].href !== pathname) router.push(TABS[idx].href);
  }, [jump, pathname, router]);

  // ── keyboard — APG tablist: roving tabindex + arrow/Home/End ─────────────
  const onKeyDown = useCallback((e: React.KeyboardEvent) => {
    const step: Record<string, number> = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
    let next: number | null = null;
    if (e.key in step) next = current + step[e.key];
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = TABS.length - 1;
    if (next === null) return;
    e.preventDefault();
    select(next, { focus: true });
  }, [current, select]);

  // ── drag — the surface follows the finger, snaps to nearest on release ───
  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0 && e.pointerType === "mouse") return;
    pidRef.current = e.pointerId;
    startXRef.current = e.clientX;
    suppressClickRef.current = false;
  }, []);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pidRef.current) return;
    if (!draggingRef.current && Math.abs(e.clientX - startXRef.current) < 7) return;
    if (!draggingRef.current) {
      draggingRef.current = true; setDragging(true); suppressClickRef.current = true;
      dockRef.current?.setPointerCapture(e.pointerId);
    }
    const left = dockRef.current?.getBoundingClientRect().left ?? 0;
    const G = geoRef.current;
    targetRef.current = clamp(e.clientX - left, G.slots[0] ?? 0, G.slots[G.slots.length - 1] ?? G.W);
    run();
  }, [run]);

  const release = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pidRef.current) return;
    pidRef.current = null;
    if (!draggingRef.current) return;
    draggingRef.current = false; setDragging(false);
    const G = geoRef.current;
    let near = 0, nd = Infinity;
    G.slots.forEach((s, i) => { const d = Math.abs(targetRef.current - s); if (d < nd) { nd = d; near = i; } });
    select(near);
    setTimeout(() => { suppressClickRef.current = false; }, 0);
  }, [select]);

  const currentAcc = TABS[current].acc;

  return (
    <nav
      aria-label="Primary"
      className="fixed left-1/2 z-50"
      style={{ bottom: "calc(env(safe-area-inset-bottom, 0px) + 16px)", transform: "translateX(-50%)", width: "min(472px, calc(100% - 24px))" }}
    >
      <div
        ref={dockRef}
        role="tablist"
        aria-orientation="horizontal"
        className="relative touch-none select-none"
        style={{
          height: 78,
          borderRadius: 24,
          background: "rgba(255,255,255,0.001)", // near-transparent, non-zero so Safari still triggers backdrop-filter
          backdropFilter: "url(#bottom-nav-glass) blur(18px) saturate(1.7)",
          WebkitBackdropFilter: "blur(18px) saturate(1.7)",
          ["--glow-rgb" as string]: hexToRgb(currentAcc).join(" "),
          filter: "drop-shadow(0 14px 32px rgba(23,24,28,0.18)) drop-shadow(0 3px 8px rgba(23,24,28,0.12))",
        }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={release}
        onPointerCancel={release}
        onKeyDown={onKeyDown}
      >
        {/* Same real liquid-glass distortion as the top bar — an SVG filter
            warps what's behind the dock (feTurbulence → feDisplacementMap),
            chained onto backdrop-filter's blur/saturate so it still reads
            as frosted glass rather than a broken image. */}
        <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden>
          <filter id="bottom-nav-glass" colorInterpolationFilters="sRGB">
            <feTurbulence type="fractalNoise" baseFrequency="0.012 0.02" numOctaves="2" seed="9" result="noise">
              <animate attributeName="baseFrequency" dur="18s" values="0.012 0.02;0.017 0.014;0.012 0.02" repeatCount="indefinite" />
            </feTurbulence>
            <feGaussianBlur in="noise" stdDeviation="3" result="softNoise" />
            <feDisplacementMap in="SourceGraphic" in2="softNoise" scale="16" xChannelSelector="R" yChannelSelector="G" />
          </filter>
        </svg>

        {/* The bar's own surface — one SVG path, notch and all, filled
            translucent so the blur above actually shows through it. The
            hairline stroke tracing the top edge is the "meniscus": the same
            border every card in the app uses, just following a curve here
            instead of a straight line. */}
        <svg ref={svgRef} width="100%" height="100%" viewBox="0 0 1 1" className="absolute inset-0 overflow-visible">
          <defs>
            <linearGradient id="liquidPlate" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.96" />
              <stop offset="100%" stopColor="#EDEAE1" stopOpacity="0.92" />
            </linearGradient>
            <linearGradient id="liquidRim" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#FFFFFF" stopOpacity="1" />
              <stop offset="55%" stopColor="#C9C4B6" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#C9C4B6" stopOpacity="0.25" />
            </linearGradient>
          </defs>
          <path ref={fillRef} fill="url(#liquidPlate)" stroke="url(#liquidRim)" strokeWidth="1.5" />
        </svg>

        {/* Tabs */}
        <div className="absolute inset-0 flex px-2.5">
          {TABS.map(({ href, label, icon: Icon }, i) => {
            const isCurrent = current === i;
            const showLabel = dragging || isCurrent;
            return (
              <button
                key={href}
                ref={(el) => { tabRefs.current[i] = el; }}
                role="tab"
                aria-selected={isCurrent}
                aria-label={label}
                tabIndex={isCurrent ? 0 : -1}
                onClick={() => { if (!suppressClickRef.current) select(i); }}
                className="relative flex-1 flex flex-col items-center justify-center gap-1.5 rounded-2xl outline-none"
                style={{ ["--t" as string]: isCurrent ? 1 : 0 }}
              >
                <Icon
                  className="relative w-[23px] h-[23px]"
                  style={{
                    color: `color-mix(in oklab, #8A8778 calc((1 - var(--t)) * 100%), #FFFFFF)`,
                    transform: "translateY(calc(var(--t) * var(--rise, 24px) * -1))",
                    transition: "color 0.15s ease",
                  }}
                  strokeWidth={isCurrent ? 2.3 : 1.9}
                />
                <span
                  className="relative text-[11px] font-semibold overflow-hidden whitespace-nowrap"
                  style={{
                    color: `rgb(var(--glow-rgb))`,
                    maxWidth: showLabel ? 84 : 0,
                    opacity: showLabel ? (isCurrent ? 1 : 0.45) : 0,
                    transition: "max-width 0.22s ease, opacity 0.18s ease",
                  }}
                >
                  {label}
                </span>
              </button>
            );
          })}
        </div>

        {/* Bead — centre pinned to the surface line, never lifts off;
            sized and positioned imperatively every frame in paint(). */}
        <div
          ref={beadRef}
          className="absolute top-0 left-0 rounded-full pointer-events-none"
          style={{
            background: `rgb(var(--glow-rgb))`,
            boxShadow: "0 0 0 1px rgba(255,255,255,0.55) inset, 0 8px 18px -6px rgba(23,24,28,0.4), 0 0 20px 2px rgb(var(--glow-rgb) / 0.32)",
            opacity: ready ? 1 : 0,
            transition: "opacity 0.2s ease",
            willChange: "transform",
          }}
        />
      </div>
    </nav>
  );
}
