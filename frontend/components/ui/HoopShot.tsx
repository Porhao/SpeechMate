"use client";

// Shoot the picked file into the hoop to upload it, like a slingshot: pull the file card back,
// a dotted line shows where it will fly (green when it's going in), and let go. It flies with
// gravity; through the rim → the net swishes and onScore() runs; a miss comes back to try again.
// The hoop is then the upload screen: the backboard shows "Uploading 75%", the net fills up and
// the file sits in it; after the upload it can list the next steps (the deck being read). Never the only way in: the page keeps its upload button (keyboard, screen
// readers), and "Shoot for me" sinks a perfect arc. Hidden with reduced motion.

import { useEffect, useRef, useState } from "react";
import { ArrowUp, Check, CheckCircle2, Circle, Loader2 } from "lucide-react";
import type { UploadPhase } from "@/components/ui/UploadCard";

const H = 370;                    // play area height (px); the width follows the container
const BOARD_H = 156;              // the backboard panel at the top
const RIM_Y = BOARD_H + 14, RIM_HALF = 40;   // rim centre height and half its width
const NET_H = 78;
const G = 1800;                   // gravity, px/s²
const BALL = { w: 44, h: 54 };
const PULL_MAX = 95, POWER = 17;  // how far it pulls back (px) and launch speed per px of pull
const IN_NET_Y = RIM_Y + NET_H - BALL.h / 2 - 4;

type Phase = "ready" | "flying" | "scored";

export type HoopStep = { label: string; state: "done" | "active" | "todo"; count?: string };

export default function HoopShot({ label, fileName, color, onScore, status, progress, processingLabel = "Reading it…", steps, fill: fillOverride }: {
  label: string; fileName: string; color: string; onScore: () => void;
  status: UploadPhase; progress: number | null; processingLabel?: string;
  steps?: HoopStep[];      // what happens after the upload, shown on the backboard
  fill?: number;           // how full the net is (0–1); by default the upload's progress
}) {
  const box = useRef<HTMLDivElement>(null);
  const ball = useRef<HTMLDivElement>(null);
  const net = useRef<SVGGElement>(null);
  const aim = useRef<SVGPolylineElement>(null);
  const st = useRef({ x: 0, y: 0, vx: 0, vy: 0, spin: 0, pulling: false, raf: 0 });
  const [phase, setPhase] = useState<Phase>("ready");
  const [misses, setMisses] = useState(0);
  const [reduced, setReduced] = useState(false);

  const width = () => box.current?.clientWidth ?? 320;
  const start = () => ({ x: width() * 0.2, y: H * 0.74 });
  const draw = () => {
    const s = st.current;
    if (ball.current) ball.current.style.transform = `translate(${s.x - BALL.w / 2}px, ${s.y - BALL.h / 2}px) rotate(${s.spin}deg)`;
  };
  const reset = () => { Object.assign(st.current, start(), { vx: 0, vy: 0, spin: 0 }); draw(); setPhase("ready"); };
  const swish = () => { const n = net.current; n?.classList.remove("net-swish"); void n?.getBoundingClientRect(); n?.classList.add("net-swish"); };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- read once on mount (window isn't there on the server)
    setReduced(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    reset();
    const s = st.current;
    return () => cancelAnimationFrame(s.raf);
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  // Uploaded with the button instead: the file drops straight into the net. A failed upload
  // (back to idle) hands the file back for another go.
  useEffect(() => {
    const s = st.current;
    if (status !== "idle" && phase === "ready") {
      cancelAnimationFrame(s.raf);
      Object.assign(s, { x: width() / 2, y: IN_NET_Y, spin: 0 });
      draw(); swish();
      setPhase("scored");  // eslint-disable-line react-hooks/set-state-in-effect -- follows the upload the page started
    } else if (status === "idle" && phase === "scored") {
      reset();
    }
  }, [status]);  // eslint-disable-line react-hooks/exhaustive-deps

  const fly = (vx: number, vy: number) => {
    const s = st.current;
    Object.assign(s, { vx, vy });
    setPhase("flying");
    let last = performance.now();
    const rimX = width() / 2;
    const step = (now: number) => {
      const dt = Math.min(0.032, (now - last) / 1000);
      last = now;
      const prevX = s.x, prevY = s.y;
      s.x += s.vx * dt; s.y += s.vy * dt + 0.5 * G * dt * dt; s.vy += G * dt; s.spin += s.vx * dt * 0.6;  // exact under gravity
      if (prevY < RIM_Y && s.y >= RIM_Y && s.vy > 0) {
        // where it crossed the rim's height, between the two frames (slow frames skip far)
        const off = prevX + (s.x - prevX) * ((RIM_Y - prevY) / (s.y - prevY)) - rimX;
        if (Math.abs(off) < RIM_HALF - 10) {           // swish
          setPhase("scored");
          swish();
          s.x = rimX + off * 0.5;
          const drop = () => {                       // settle into the net, then upload
            s.y = Math.min(IN_NET_Y, s.y + 5); s.x += (rimX - s.x) * 0.2; s.spin *= 0.85; draw();
            if (s.y < IN_NET_Y) s.raf = requestAnimationFrame(drop); else setTimeout(onScore, 120);
          };
          s.raf = requestAnimationFrame(drop);
          return;
        }
        if (Math.abs(off) < RIM_HALF + 14) {          // clanged off the rim
          s.vy = -s.vy * 0.45; s.vx += Math.sign(off || 1) * 160; s.y = RIM_Y - 1;
        }
      }
      if (s.y < BALL.h / 2) { s.y = BALL.h / 2; s.vy = Math.abs(s.vy) * 0.3; }    // ceiling
      if (s.x < -60 || s.x > width() + 60 || s.y > H + 60) {                     // missed
        setMisses((m) => m + 1);
        reset();
        return;
      }
      draw();
      s.raf = requestAnimationFrame(step);
    };
    s.raf = requestAnimationFrame(step);
  };

  // An arc through the rim's centre, arriving on the way down (its peak stays below the top edge)
  const autoShoot = () => {
    if (phase !== "ready") return;
    const s = st.current, T = 0.5;
    fly((width() / 2 - s.x) / T, (RIM_Y - s.y) / T - 0.5 * G * T);
  };

  // The launch for the current pull: opposite the pull, stronger the further back
  const launch = () => {
    const s = st.current, o = start();
    return { vx: (o.x - s.x) * POWER, vy: (o.y - s.y) * POWER, pull: Math.hypot(s.x - o.x, s.y - o.y) };
  };

  // The dotted aim line: the same flight, until it reaches the rim's height on the way down
  const preview = () => {
    const el = aim.current;
    if (!el) return;
    const s = st.current, { vx, vy, pull } = launch();
    if (pull < 12) { el.setAttribute("points", ""); return; }
    const pts: string[] = [];
    let x = s.x, y = s.y, v = vy, inHoop = false;
    for (let i = 0; i < 60; i++) {
      const px = x, py = y, dt = 1 / 40;
      x += vx * dt; y += v * dt + 0.5 * G * dt * dt; v += G * dt;
      if (py < RIM_Y && y >= RIM_Y && v > 0) {
        const cx = px + (x - px) * ((RIM_Y - py) / (y - py));
        inHoop = Math.abs(cx - width() / 2) < RIM_HALF - 10;
        pts.push(`${cx},${RIM_Y}`);
        break;
      }
      if (y < BALL.h / 2 || y > H || x < 0 || x > width()) break;   // where the real flight would hit the top
      pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    el.setAttribute("points", `${s.x},${s.y} ${pts.join(" ")}`);
    el.style.stroke = inHoop ? "var(--ok)" : "var(--muted)";
  };

  const onDown = (e: React.PointerEvent) => {
    if (phase !== "ready" || status !== "idle") return;
    e.currentTarget.setPointerCapture(e.pointerId);
    st.current.pulling = true;
  };
  const onMove = (e: React.PointerEvent) => {
    const s = st.current;
    if (phase !== "ready" || !s.pulling || !box.current) return;
    const r = box.current.getBoundingClientRect(), o = start();
    let dx = e.clientX - r.left - o.x, dy = e.clientY - r.top - o.y;
    const d = Math.hypot(dx, dy);
    if (d > PULL_MAX) { dx *= PULL_MAX / d; dy *= PULL_MAX / d; }
    s.x = o.x + dx; s.y = Math.min(H - BALL.h / 2, o.y + dy);   // stays inside the court
    draw(); preview();
  };
  const onUp = () => {
    const s = st.current;
    if (!s.pulling) return;
    s.pulling = false;
    aim.current?.setAttribute("points", "");
    const { vx, vy, pull } = launch();
    if (phase !== "ready" || pull < 12) { reset(); return; }   // a tap isn't a shot
    fly(vx, vy);
  };

  if (reduced) return null;

  const pct = Math.round((progress ?? 0) * 100);
  const fill = fillOverride ?? (status === "uploading" ? pct / 100 : status === "idle" ? 0 : 1);
  const Icon = status === "done" ? Check : status === "processing" ? Loader2 : ArrowUp;
  const head = status === "uploading" ? <>Uploading <span className="tabular-nums">{pct}%</span></>
    : status === "processing" ? processingLabel : status === "done" ? "Uploaded" : "Shoot to upload";

  return (
    <div className="space-y-2">
      <div ref={box} className="relative rounded-xl overflow-hidden select-none touch-none" style={{ height: H, background: "var(--bg)", border: "1px solid var(--line)" }}>
        {/* The backboard: also the upload status */}
        <div className="absolute left-1/2 -translate-x-1/2 rounded-2xl px-4 pt-3" aria-live="polite"
          style={{ top: 12, height: BOARD_H, width: "min(400px, calc(100% - 24px))", border: `1.5px dashed ${color}`, background: `color-mix(in srgb, ${color} 7%, var(--surface))` }}>
          <div className="flex items-center gap-3">
            <span className="w-9 h-9 flex-shrink-0 rounded-full flex items-center justify-center text-white" style={{ background: status === "done" ? "var(--ok)" : color }}>
              <Icon className={`w-5 h-5 ${status === "processing" ? "animate-spin" : ""}`} strokeWidth={2.5} />
            </span>
            <span className="min-w-0">
              <span className="block font-display text-xl leading-tight" style={{ color: "var(--ink)" }}>{head}</span>
              <span className="block text-xs truncate" style={{ color: "var(--muted)" }}>{fileName}</span>
            </span>
          </div>
          {steps && status !== "idle" && (
            <ul className="mt-2 space-y-1 text-xs">
              {steps.map((st) => (
                <li key={st.label} className="flex items-center gap-2" style={{ color: st.state === "todo" ? "var(--faint)" : "var(--ink)", fontWeight: st.state === "active" ? 600 : 400 }}>
                  {st.state === "done" ? <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" style={{ color: "var(--ok)" }} />
                    : st.state === "active" ? <Loader2 className="w-3.5 h-3.5 flex-shrink-0 animate-spin" style={{ color }} />
                    : <Circle className="w-3.5 h-3.5 flex-shrink-0" />}
                  <span className="truncate">{st.label}</span>
                  {st.count && <span className="ml-auto tabular-nums" style={{ color: "var(--muted)" }}>{st.count}</span>}
                </li>
              ))}
            </ul>
          )}
          {/* the square on the board you aim over */}
          <span className="absolute left-1/2 -translate-x-1/2 rounded-sm" style={{ bottom: 6, width: 74, height: 46, border: `2.5px solid ${color}` }} />
        </div>

        {/* Net fill (the upload progress), behind the file */}
        <svg className="absolute left-1/2 -translate-x-1/2 pointer-events-none" style={{ top: RIM_Y }} width="100" height={NET_H} viewBox={`0 0 100 ${NET_H}`} aria-hidden>
          <clipPath id="net-fill"><rect x="0" y={NET_H * (1 - fill)} width="100" height={NET_H * fill} style={{ transition: "y 0.3s, height 0.3s" }} /></clipPath>
          <path d={`M8 0 H92 L74 ${NET_H} H26 Z`} fill={color} opacity="0.85" clipPath="url(#net-fill)" />
        </svg>

        {/* Where the shot will go */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" aria-hidden>
          <polyline ref={aim} points="" fill="none" strokeWidth="3" strokeLinecap="round" strokeDasharray="0.1 9" />
        </svg>

        {/* The file */}
        <div ref={ball} role="img" aria-label={`${label}: pull back, aim and let go to shoot`}
          onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}
          className={`absolute left-0 top-0 rounded-lg flex flex-col items-center justify-end pb-1.5 ${phase === "ready" ? "cursor-grab active:cursor-grabbing" : ""}`}
          style={{ width: BALL.w, height: BALL.h, background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow-card)", willChange: "transform" }}>
          <span className="w-6 h-0.5 rounded mb-1" style={{ background: "var(--line-strong)" }} />
          <span className="w-6 h-0.5 rounded mb-1.5" style={{ background: "var(--line-strong)" }} />
          <span className="text-[9px] font-bold px-1 rounded text-white" style={{ background: color }}>{label}</span>
        </div>

        {/* Rim and net strings in front of the file, so it drops *through* the hoop */}
        <svg className="absolute left-1/2 -translate-x-1/2 pointer-events-none" style={{ top: RIM_Y - 7 }} width="100" height={NET_H + 9} viewBox={`0 -7 100 ${NET_H + 9}`} aria-hidden>
          <g ref={net} className="origin-top" style={{ transformBox: "fill-box" }}>
            {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
              <line key={i} x1={8 + i * 12} y1="0" x2={26 + i * 6.9} y2={NET_H} stroke="var(--faint)" strokeWidth="1.3" />
            ))}
            {[0.3, 0.55, 0.8].map((f) => (
              <line key={f} x1={8 + 18 * f} y1={NET_H * f} x2={92 - 18 * f} y2={NET_H * f} stroke="var(--faint)" strokeWidth="1.1" />
            ))}
          </g>
          <ellipse cx="50" cy="0" rx="44" ry="5.5" fill="none" stroke={color} strokeWidth="4.5" />
        </svg>

        {status === "idle" && (
          <p className="absolute bottom-2 right-3 text-xs" style={{ color: "var(--muted)" }}>
            {phase === "scored" ? "Swish!" : misses > 0 && phase === "ready" ? (misses > 1 ? "Pull back until the dotted line turns green" : "So close! Try again") : "Pull the file back, aim, and let go"}
          </p>
        )}
      </div>
      {status === "idle" && (
        <button type="button" onClick={autoShoot} disabled={phase !== "ready"} className="text-xs font-semibold underline disabled:opacity-40" style={{ color: "var(--accent-ink)" }}>
          Shoot for me
        </button>
      )}
    </div>
  );
}
