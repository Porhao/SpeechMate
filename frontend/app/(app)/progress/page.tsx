"use client";

// Your progress from real sessions only: totals, how the overall score and the four
// pillars have moved, and every session (open one for its full results).

import { useEffect, useMemo, useState } from "react";
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

// A small line chart (oldest → newest), 0–100
function Trend({ values, height = 120 }: { values: number[]; height?: number }) {
  if (values.length < 2) {
    return <p className="text-sm py-6" style={{ color: "var(--muted)" }}>Complete two analysed sessions to see a trend.</p>;
  }
  const w = 600, pad = 8;
  const x = (i: number) => pad + (i * (w - pad * 2)) / (values.length - 1);
  const y = (v: number) => pad + (1 - v / 100) * (height - pad * 2);
  const d = values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full" style={{ height }} role="img"
      aria-label={`Scores over ${values.length} sessions, from ${values[0]} to ${values[values.length - 1]}`}>
      {[25, 50, 75].map((g) => <line key={g} x1={0} x2={w} y1={y(g)} y2={y(g)} stroke="var(--line-2)" strokeWidth={1} />)}
      <path d={d} fill="none" stroke="var(--accent-ink)" strokeWidth={2} />
      {values.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r={3} fill="var(--accent-ink)" />)}
    </svg>
  );
}

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
  const overallSeries = analysed.map(overall).filter((v): v is number => v != null);
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
                className="px-3 h-8 text-sm"
                style={{ background: type === t.id ? "var(--accent)" : "var(--surface)", color: type === t.id ? "#fff" : "var(--ink-2)", border: "1px solid var(--line-strong)" }}>
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
              <div key={k} className="p-4" style={{ background: "var(--surface)", border: "1px solid var(--line)" }}>
                <p className="text-xs" style={{ color: "var(--muted)" }}>{k}</p>
                <p className="font-display text-2xl mt-1 tabular-nums" style={{ color: "var(--ink)" }}>{v}</p>
              </div>
            ))}
          </div>

          <Card title="Overall score per session"><Trend values={overallSeries} /></Card>

          <div className="grid sm:grid-cols-2 gap-3">
            {PILLARS.map((p) => {
              const series = analysed.map((s) => s.analysis?.pillars?.[p.key]?.score).filter((v): v is number => v != null).map(Math.round);
              const last = series.length ? series[series.length - 1] : null;
              return (
                <Card key={p.key} title={p.label}
                  action={<span className="text-sm font-semibold tabular-nums" style={{ color: statusColor(statusOf(last)) }}>{last ?? "—"}</span>}>
                  <Trend values={series} height={70} />
                </Card>
              );
            })}
          </div>

          <Card title="All sessions">
            <ul className="divide-y" style={{ borderColor: "var(--line-2)" }}>
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
                          {TYPE_LABEL[s.session_type] ?? s.session_type}{subtitle(s) ? ` · ${subtitle(s)}` : ""}
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
