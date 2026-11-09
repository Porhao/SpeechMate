// "Crumple and toss": a deleted row scrunches into a paper ball that arcs into Mate's mouth (the
// companion in the corner opens wide and chomps it), or, when Mate is tucked away or not loaded,
// into a bin whose lid flips, squashes on the landing and puffs a little dust.
// Everything is drawn in a fixed overlay with the Web Animations API, so the row itself is free
// to fold away (hooks/useExit.ts). Skipped with reduced motion.

import { mascot } from "@/lib/mascot";

const PAPER = "radial-gradient(circle at 35% 30%, #FFFFFF, #ECE7DC 60%, #D6CFC0)";
const BALL = 30;
const TOSS_MS = 560;

function el(css: Partial<CSSStyleDeclaration>, html = ""): HTMLDivElement {
  const d = document.createElement("div");
  Object.assign(d.style, { position: "fixed", zIndex: "100", pointerEvents: "none" }, css);
  d.innerHTML = html;
  document.body.appendChild(d);
  return d;
}

function puff(x: number, y: number, bits: [number, number][], css: Partial<CSSStyleDeclaration>, delay = 0) {
  for (const [dx, dy] of bits) {
    const b = el({ left: `${x}px`, top: `${y}px`, width: "7px", height: "7px", ...css });
    b.animate([{ transform: "none", opacity: 0.9 }, { transform: `translate(${dx}px, ${dy}px) rotate(90deg) scale(0.3)`, opacity: 0 }],
      { duration: 460, delay, easing: "ease-out" }).onfinish = () => b.remove();
  }
}

/** The row scrunches into a ball, then arcs (spinning) to the centre point (tx, ty). */
function crumpleTo(r: DOMRect, tx: number, ty: number, endScale: number, onThrow: () => void, onLand: () => void) {
  const paper = el({
    left: `${r.left}px`, top: `${r.top}px`, width: `${r.width}px`, height: `${r.height}px`,
    background: PAPER, borderRadius: "10px", boxShadow: "0 6px 16px rgba(0,0,0,0.18)",
  });
  const cx = r.left + r.width / 2 - BALL / 2, cy = r.top + r.height / 2 - BALL / 2;
  paper.animate([
    { opacity: 0.9 },
    { left: `${cx - 10}px`, top: `${cy - 6}px`, width: `${BALL + 20}px`, height: `${BALL + 12}px`, borderRadius: "40%", transform: "rotate(-25deg)", offset: 0.6 },
    { left: `${cx}px`, top: `${cy}px`, width: `${BALL}px`, height: `${BALL}px`, borderRadius: "50%", transform: "rotate(40deg)", opacity: 1 },
  ], { duration: 320, easing: "cubic-bezier(0.6,0,0.4,1)", fill: "forwards" }).onfinish = () => {
    const ex = tx - BALL / 2, ey = ty - BALL / 2;
    const lift = Math.max(110, Math.hypot(ex - cx, ey - cy) * 0.35);
    const frames: Keyframe[] = [];
    for (let i = 0; i <= 16; i++) {
      const p = i / 16;
      frames.push({
        left: `${cx + (ex - cx) * p}px`, top: `${cy + (ey - cy) * p - lift * Math.sin(Math.PI * p)}px`,
        width: `${BALL}px`, height: `${BALL}px`, borderRadius: "50%",
        transform: `rotate(${40 + 540 * p}deg) scale(${1 - (1 - endScale) * p})`,
      });
    }
    onThrow();
    paper.animate(frames, { duration: TOSS_MS, easing: "cubic-bezier(0.3,0.1,0.5,1)", fill: "forwards" }).onfinish = () => {
      paper.remove();
      onLand();
    };
  };
}

export function crumpleAndToss(row: Element | null) {
  if (!row || typeof window === "undefined" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const r = row.getBoundingClientRect();

  // Mate is on screen: into its mouth. Its mouth opens as the ball flies (Mascot.tsx) and chomps.
  const mouth = document.querySelector("[data-mascot-mouth]");
  const m = mouth?.getClientRects().length ? mouth.getBoundingClientRect() : null;
  if (m) {
    crumpleTo(r, m.left, m.top, 0.3, () => mascot("eat"),
      () => puff(m.left - 3, m.top - 3, [[-16, -10], [14, -14], [6, 12]], { borderRadius: "2px", background: "#E4DED2" }, 150));
    return;
  }

  // Otherwise a bin in the corner: a body and a lid that flips open
  const bin = el({ right: "28px", bottom: "28px", width: "56px", height: "64px", transformOrigin: "50% 100%" }, `
    <svg viewBox="0 0 56 64" width="56" height="64" style="overflow:visible">
      <g class="lid" style="transform-origin:46px 12px"><rect x="4" y="6" width="48" height="7" rx="3" fill="#5B6478"/><rect x="21" y="1" width="14" height="6" rx="2" fill="#5B6478"/></g>
      <path d="M8 16 H48 L44 62 H12 Z" fill="#3F4658"/>
      <path d="M20 24 V54 M28 24 V54 M36 24 V54" stroke="#69728A" stroke-width="2.5" stroke-linecap="round"/>
    </svg>`);
  const lid = bin.querySelector<SVGGElement>(".lid")!;
  bin.animate([{ opacity: 0, transform: "translateY(16px) scale(0.8)" }, { opacity: 1, transform: "none" }], { duration: 220, fill: "forwards" });
  const tx = window.innerWidth - 28 - 28, ty = window.innerHeight - 28 - 64 + 6 + BALL / 2;
  crumpleTo(r, tx, ty, 0.75,
    () => lid.animate([{ transform: "rotate(0)" }, { transform: "rotate(-55deg)" }], { duration: 260, delay: 260, fill: "forwards", easing: "ease-out" }),
    () => {
      lid.animate([{ transform: "rotate(-55deg)" }, { transform: "rotate(8deg)" }, { transform: "rotate(0)" }], { duration: 260, fill: "forwards" });
      bin.animate([{ transform: "none" }, { transform: "scale(1.08, 0.88)" }, { transform: "scale(0.96, 1.04)" }, { transform: "none" }], { duration: 360 });
      const b = bin.getBoundingClientRect();
      puff(b.left + 26, b.top + 8, [[-26, -14], [-14, -26], [0, -30], [14, -26], [26, -14]], { borderRadius: "50%", background: "#C9C2B4" });
      bin.animate([{ opacity: 1 }, { opacity: 0, transform: "translateY(12px)" }], { duration: 260, delay: 700, fill: "forwards" }).onfinish = () => bin.remove();
    });
}
