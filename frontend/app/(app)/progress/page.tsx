"use client";

// Your progress from real sessions only: totals, how the overall score and the four
// pillars have moved, and every session (open one for its full results).

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ChevronRight, Loader2, Trash2 } from "lucide-react";
import { liveService } from "@/services/live";
import { authService } from "@/services/auth";
import { Card, LinkButton, Notice, PageHeader, statusColor } from "@/components/ui/kit";
import type { LiveSession, MetricStatus } from "@/types";
import { formatDuration } from "@/utils/format";

const TYPES = [
  { id: "all", label: "All" },
  { id: "Conversation", label: "Conversation" },
  { id: "Interview", label: "Interview" },
  { id: "Presentation", label: "Presentation Q&A" },
] as const;
const TYPE_LABEL: Record<string, string> = { Conversation: "Conversation", Interview: "Mock interview", Presentation: "Presentation Q&A", Pronunciation: "Pronunciation" };
const PILLARS = [
  { key: "voice", label: "Voice & delivery" },
  { key: "language", label: "Language & clarity" },
  { key: "body", label: "Body language" },
  { key: "confidence", label: "Confidence & presence" },
] as const;

const statusOf = (v: number | null): MetricStatus => (v == null ? null : v >= 75 ? "good" : v >= 55 ? "ok" : "work");

function overall(s: LiveSession): number | null {
  const a = s.analysis;
  if (!a) return null;
  if (a.communication_score.overall_score != null) return Math.round(a.communication_score.overall_score);
  const vals = PILLARS.map((p) => a.pillars?.[p.key]?.score).filter((v): v is number => v != null);
  return vals.length ? Math.round(vals.reduce((x, y) => x + y, 0) / vals.length) : null;
}

function subtitle(s: LiveSession) {
  if (s.session_type === "Interview") return s.context?.setup?.position;
  if (s.session_type === "Presentation") return s.context?.deck_title;
  return s.context?.topic;
}

type Point = { v: number; date: string; label?: string };  // label: shown in the tooltip instead of v

// One score over time (oldest → newest, 0–100): a single 2px line in the accent ink, a dashed
// "Strong" reference at 75, Best and Latest marked, a crosshair + tooltip on hover/focus, and a
// table view for screen readers and anyone who prefers numbers.
function Trend({ points, height = 140, title }: { points: Point[]; height?: number; title: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  // Draw at the real pixel width, so lines stay 2px and labels stay legible at any card size
  const box = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(600);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(240, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [table]);
  if (points.length < 2) {
    return <p className="text-sm py-6" style={{ color: "var(--muted)" }}>Complete two analysed sessions to see a trend.</p>;
  }
  const top = 18, bottom = 18, left = 28, right = 14;
  const x = (i: number) => left + (i * (w - left - right)) / (points.length - 1);
  const y = (v: number) => top + (1 - v / 100) * (height - top - bottom);
  const d = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
  const best = points.reduce((bi, p, i) => (p.v > points[bi].v ? i : bi), 0);
  const last = points.length - 1;
  const fmtDate = (iso: string) => new Date(iso).toLocaleDateString("en-MY", { day: "numeric", month: "short" });
  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * w;
    setHover(Math.max(0, Math.min(last, Math.round(((px - left) / (w - left - right)) * last))));
  };
  const h = hover != null ? points[hover] : null;
  return (
    <div>
      <div className="flex justify-end -mt-1 mb-1">
        <button onClick={() => setTable((t) => !t)} className="text-xs font-semibold" style={{ color: "var(--accent-ink)" }} aria-pressed={table}>
          {table ? "Show chart" : "Show as table"}
        </button>
      </div>
      {table ? (
        <table className="w-full text-sm">
          <caption className="sr-only">{title}</caption>
          <thead><tr style={{ color: "var(--muted)" }}><th className="text-left font-medium py-1">Session</th><th className="text-right font-medium py-1">Score</th></tr></thead>
          <tbody>
            {points.map((p, i) => (
              <tr key={i} style={{ borderTop: "1px solid var(--line-2)", color: "var(--ink-2)" }}>
                <td className="py-1.5">{fmtDate(p.date)}{i === best ? " · best" : ""}</td>
                <td className="py-1.5 text-right tabular-nums">{p.label ?? p.v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="relative" ref={box}>
          <svg viewBox={`0 0 ${w} ${height}`} className="w-full touch-none" style={{ height }} role="img" tabIndex={0}
            aria-label={`${title}: ${points.length} sessions, from ${points[0].label ?? points[0].v} to ${points[last].label ?? points[last].v}; best ${points[best].label ?? points[best].v}. Use the table view for every value.`}
            onPointerMove={onMove} onPointerLeave={() => setHover(null)}
            onKeyDown={(e) => {
              if (e.key === "ArrowRight") setHover((v) => Math.min(last, (v ?? -1) + 1));
              if (e.key === "ArrowLeft") setHover((v) => Math.max(0, (v ?? last + 1) - 1));
            }}
            onBlur={() => setHover(null)}>
            {[0, 50, 100].map((g) => (
              <g key={g}>
                <line x1={left} x2={w - right} y1={y(g)} y2={y(g)} stroke="var(--line-2)" strokeWidth={1} />
                <text x={left - 6} y={y(g) + 3} textAnchor="end" fontSize={10} fill="var(--muted)">{g}</text>
              </g>
            ))}
            <line x1={left} x2={w - right} y1={y(75)} y2={y(75)} stroke="var(--line-strong)" strokeWidth={1} strokeDasharray="4 4" />
            <text x={left + 4} y={y(75) + 12} fontSize={10} fill="var(--muted)">Strong (75)</text>
            <path d={d} fill="none" stroke="var(--accent-ink)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
            {h && <line x1={x(hover!)} x2={x(hover!)} y1={top} y2={height - bottom} stroke="var(--line-strong)" strokeWidth={1} />}
            {points.map((p, i) => (
              <circle key={i} cx={x(i)} cy={y(p.v)} r={i === hover ? 5 : 4} fill="var(--accent-ink)" stroke="var(--surface)" strokeWidth={2} />
            ))}
            {[best, last].filter((i, k, a) => a.indexOf(i) === k).map((i) => (
              <text key={i} x={x(i)} y={y(points[i].v) - 10} textAnchor={i === last ? "end" : "middle"} fontSize={11} fontWeight={600} fill="var(--ink)">
                {i === best && i === last ? `Best · ${points[i].label ?? points[i].v}` : i === best ? `Best ${points[i].label ?? points[i].v}` : `${points[i].label ?? points[i].v}`}
              </text>
            ))}
          </svg>
          {h && (
            <div className="absolute top-0 pointer-events-none px-2.5 py-1.5 rounded-md text-xs shadow-md"
              style={{ left: `${(x(hover!) / w) * 100}%`, transform: `translateX(${hover! > last / 2 ? "-105%" : "5%"})`, background: "var(--surface)", border: "1px solid var(--line)", color: "var(--ink)" }}>
              <b className="tabular-nums">{h.label ?? h.v}</b> <span style={{ color: "var(--muted)" }}>· {fmtDate(h.date)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// The metric behind a coaching area, as named in the pillars (a few differ)
const AREA_METRIC: Record<string, string> = { volume: "loudness", repetitions: "disfluency" };

export default function ProgressPage() {
  const [list, setList] = useState<LiveSession[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [type, setType] = useState<(typeof TYPES)[number]["id"]>("all");

  useEffect(() => {
    if (!authService.isSignedIn()) {
      const t = setTimeout(() => setError("Sign in to see your progress."), 0);
      return () => clearTimeout(t);
    }
    liveService.history().then(setList).catch((e) => setError(e instanceof Error ? e.message : "Couldn't load your sessions"));
  }, []);

  const shown = useMemo(() => (list ?? []).filter((s) => type === "all" || s.session_type === type), [list, type]);
  const analysed = useMemo(() => shown.filter((s) => s.status === "complete").slice().reverse(), [shown]);  // oldest first
  const overallPoints: Point[] = analysed.flatMap((s) => { const v = overall(s); return v != null ? [{ v, date: s.created_at }] : []; });
  const overallSeries = overallPoints.map((p) => p.v);
  // The latest #1 focus, tracked across sessions through the metric it's measured by
  const focusEx = analysed.at(-1)?.analysis?.recommendations.exercises[0];
  const focusKey = focusEx?.area ? AREA_METRIC[focusEx.area] ?? focusEx.area : null;
  const focusPoints: Point[] = focusKey ? analysed.flatMap((s) => {
    const m = PILLARS.flatMap((p) => s.analysis?.pillars?.[p.key]?.metrics ?? []).find((mm) => mm.key === focusKey);
    return m?.score != null ? [{ v: Math.round(m.score), date: s.created_at, label: m.display }] : [];
  }) : [];
  const minutes = Math.round(shown.reduce((t, s) => t + s.duration_sec, 0) / 60);

  const remove = async (id: string) => {
    if (!confirm("Delete this session and its results? This can't be undone.")) return;
    await liveService.remove(id).catch(() => null);
    setList((l) => l?.filter((s) => s.id !== id) ?? null);
  };

  return (
    <div className="px-4 sm:px-6 py-8 max-w-[1100px] mx-auto space-y-6">
      <PageHeader eyebrow="Progress" title="How you're improving">
        Every number here comes from your own analysed sessions.
      </PageHeader>

      {error && <Notice tone="warn">{error} {error.startsWith("Sign in") && <Link href="/login" className="underline">Sign in</Link>}</Notice>}
      {!list && !error && <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--muted)" }} /></div>}

      {list && list.length === 0 && (
        <Card>
          <p className="text-sm mb-4" style={{ color: "var(--ink-2)" }}>No sessions yet. Start with a short conversation to get your first results.</p>
          <LinkButton href="/conversation">Start a conversation</LinkButton>
        </Card>
      )}

      {list && list.length > 0 && (
        <>
          <div className="flex flex-wrap gap-2" role="tablist">
            {TYPES.map((t) => (
              <button key={t.id} role="tab" aria-selected={type === t.id} onClick={() => setType(t.id)}
                className={`nav-pill px-4 py-2 rounded-full text-sm font-medium ${type === t.id ? "nav-pill-active" : ""}`}>
                {t.label}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              ["Sessions", String(shown.length)],
              ["Practice time", minutes >= 60 ? `${(minutes / 60).toFixed(1)} h` : `${minutes} min`],
              ["Latest overall", overallSeries.length ? String(overallSeries[overallSeries.length - 1]) : "—"],
              ["Change since first", overallSeries.length >= 2 ? `${overallSeries[overallSeries.length - 1] - overallSeries[0] >= 0 ? "+" : ""}${overallSeries[overallSeries.length - 1] - overallSeries[0]}` : "—"],
            ].map(([k, v]) => (
              <div key={k} className="p-4 rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow-card)" }}>
                <p className="text-xs" style={{ color: "var(--muted)" }}>{k}</p>
                <p className="font-display text-2xl mt-1 tabular-nums" style={{ color: "var(--ink)" }}>{v}</p>
              </div>
            ))}
          </div>

          {focusEx && focusPoints.length > 0 && (
            <div className="clay rounded-xl p-5 sm:p-6" style={{ background: "var(--peach)", color: "#0A0A0A" }}>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] opacity-70">Your #1 focus</p>
              <p className="font-display text-2xl mt-1">{focusEx.title}</p>
              <p className="text-sm mt-1 opacity-80">Its score in each session (0–100), with your measured value on hover.</p>
              <div className="mt-3 rounded-lg p-3" style={{ background: "#FFFAF0" }}>
                <Trend points={focusPoints} height={110} title={`${focusEx.title} over time`} />
              </div>
            </div>
          )}

          <Card title="Overall score per session"><Trend points={overallPoints} title="Overall score per session" /></Card>

          <div className="grid sm:grid-cols-2 gap-3">
            {PILLARS.map((p) => {
              const pts: Point[] = analysed.flatMap((s) => {
                const v = s.analysis?.pillars?.[p.key]?.score;
                return v != null ? [{ v: Math.round(v), date: s.created_at }] : [];
              });
              const last = pts.length ? pts[pts.length - 1].v : null;
              return (
                <Card key={p.key} title={p.label}
                  action={<span className="text-sm font-semibold tabular-nums" style={{ color: statusColor(statusOf(last)) }}>{last ?? "—"}</span>}>
                  <Trend points={pts} height={100} title={`${p.label} per session`} />
                </Card>
              );
            })}
          </div>

          <Card title="All sessions">
            <ul className="divide-y divide-[var(--line-2)]">
              {shown.map((s) => {
                const score = overall(s);
                return (
                  <li key={s.id} className="flex items-center gap-3 py-3">
                    <Link href={`/results/${s.id}`} className="flex-1 min-w-0 flex items-center gap-4 group">
                      <span className="w-12 text-center font-display text-xl tabular-nums" style={{ color: score != null ? statusColor(statusOf(score)) : "var(--faint)" }}>
                        {score ?? "—"}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-medium truncate" style={{ color: "var(--ink)" }}>
                          {s.context?.kind === "talk" ? "Presentation" : TYPE_LABEL[s.session_type] ?? s.session_type}{subtitle(s) ? ` · ${subtitle(s)}` : ""}
                        </span>
                        <span className="block text-xs" style={{ color: "var(--muted)" }}>
                          {new Date(s.created_at).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" })} · {formatDuration(s.duration_sec)}
                          {s.status !== "complete" && ` · ${s.status === "analyzing" ? "analysing…" : s.status === "failed" ? "analysis failed" : "not analysed"}`}
                        </span>
                      </span>
                      <ChevronRight className="w-4 h-4 opacity-40 group-hover:opacity-100" style={{ color: "var(--ink)" }} />
                    </Link>
                    <button onClick={() => remove(s.id)} aria-label="Delete session" className="p-2 opacity-50 hover:opacity-100" style={{ color: "var(--muted)" }}>
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </li>
                );
              })}
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}
