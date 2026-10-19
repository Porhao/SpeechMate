"use client";

// "My tasks": what to practise next, built from your own sessions and decks, plus what's
// still running. Two tabs:
//   Due today & late: the drills from your latest session in each mode, decks waiting to be
//     presented or rehearsed, analyses to retry, and a daily practice reminder; tick them off.
//   In progress: decks being prepared and sessions being analysed, with their live status.
// Ticks are kept per account on this device.
// ponytail: ticks live in localStorage; move them to the server if they must follow you across devices.

import { useMemo, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { Check, Flag, Loader2 } from "lucide-react";
import { mascot } from "@/lib/mascot";
import { deckProgress } from "@/lib/deckPipeline";
import { DECK_IN_PROGRESS } from "@/services/presentation";
import type { DeckListItem, LiveSession } from "@/types";

type Priority = "Urgent" | "High" | null;
interface Task { id: string; title: string; tag: keyof typeof TAGS; due: Date; priority: Priority; href: string }
interface Pending { id: string; title: string; tag: keyof typeof TAGS; status: string; href: string }

const TAGS = {
  Conversation: { label: "Conversation", dot: "var(--pink)" },
  Interview: { label: "Mock interview", dot: "var(--teal-ink)" },
  Presentation: { label: "Presentation", dot: "var(--lavender)" },
  Daily: { label: "Daily practice", dot: "var(--peach)" },
} as const;
const DAY = 86_400_000;
const SHOW = 6;
const CELEBRATE_MS = 900;   // .task-celebrate in globals.css
const CONFETTI = [[-22, -18], [20, -20], [26, 6], [-26, 8], [-4, -28], [10, 24], [-16, 22], [28, -8]] as const;
const CONFETTI_COLORS = ["var(--pink)", "var(--peach)", "var(--lavender)", "var(--ok)"];

const startOfDay = (d: Date) => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; };
const plusDays = (iso: string, n: number) => new Date(startOfDay(new Date(iso)).getTime() + n * DAY);

function dueLabel(due: Date): { text: string; late: boolean } {
  const days = Math.round((startOfDay(due).getTime() - startOfDay(new Date()).getTime()) / DAY);
  if (days < 0) return { text: days === -1 ? "Yesterday" : `${-days} days late`, late: true };
  if (days === 0) return { text: "Today", late: false };
  if (days === 1) return { text: "Tomorrow", late: false };
  return { text: due.toLocaleDateString("en-MY", { day: "numeric", month: "short" }), late: false };
}

const modeOf = (s: LiveSession): keyof typeof TAGS => (s.session_type in TAGS ? s.session_type as keyof typeof TAGS : "Conversation");

function buildTasks(sessions: LiveSession[], decks: DeckListItem[]): { due: Task[]; pending: Pending[] } {
  const due: Task[] = [];
  const today = startOfDay(new Date());
  // A reminder for today, until there's a session today
  if (!sessions.some((s) => startOfDay(new Date(s.created_at)).getTime() === today.getTime())) {
    due.push({ id: `daily-${today.toISOString().slice(0, 10)}`, title: "Practise for 5 minutes today", tag: "Daily", due: today, priority: null, href: "/conversation" });
  }
  // The drills from the latest analysed session of each mode (due two days after it)
  const seen = new Set<string>();
  for (const s of sessions) {  // newest first
    if (s.status !== "complete" || seen.has(s.session_type)) continue;
    seen.add(s.session_type);
    (s.analysis?.recommendations.exercises ?? []).slice(0, 3).forEach((ex, i) => due.push({
      id: `drill-${s.id}-${i}`, title: `Drill: ${ex.title}`, tag: modeOf(s),
      due: plusDays(s.created_at, 2), priority: i === 0 ? "High" : null, href: `/results/${s.id}`,
    }));
  }
  // Recordings whose analysis failed
  for (const s of sessions.filter((x) => x.status === "failed" && x.has_recording)) {
    due.push({ id: `retry-${s.id}`, title: "Retry the analysis of this session", tag: modeOf(s), due: new Date(s.created_at), priority: "Urgent", href: `/results/${s.id}` });
  }
  // Decks: present the ready ones, then rehearse their Q&A; fix the ones that failed
  for (const d of decks) {
    const p = deckProgress(d, sessions);
    const name = d.original_filename.replace(/\.(pptx|pdf)$/i, "");
    if (d.status === "failed") due.push({ id: `deck-failed-${d.session_id}`, title: `Retry preparing “${name}”`, tag: "Presentation", due: new Date(d.created_at), priority: "Urgent", href: `/presentations/${d.session_id}` });
    else if (p.stage === "ready") due.push({ id: `deck-present-${d.session_id}`, title: `Present “${name}”`, tag: "Presentation", due: plusDays(d.created_at, 2), priority: "High", href: `/presentations/${d.session_id}` });
    else if (p.stage === "presented") due.push({ id: `deck-qa-${d.session_id}`, title: `Rehearse the Q&A for “${name}”`, tag: "Presentation", due: plusDays(p.lastAt ?? d.created_at, 2), priority: null, href: `/presentations/${d.session_id}` });
  }
  due.sort((a, b) => a.due.getTime() - b.due.getTime() || (a.priority === "Urgent" ? -1 : 0));

  const pending: Pending[] = [
    ...decks.filter((d) => DECK_IN_PROGRESS.has(d.status)).map((d) => ({
      id: d.session_id, title: d.original_filename, tag: "Presentation" as const,
      status: d.status === "queued" ? "Waiting to be read" : "Reading the slides…", href: `/presentations/${d.session_id}`,
    })),
    ...sessions.filter((s) => s.status === "analyzing" || (s.status === "active" && s.has_recording)).map((s) => ({
      id: s.id, title: TAGS[modeOf(s)].label, tag: modeOf(s),
      status: s.status === "analyzing" ? "Analysing your recording…" : "Recorded, not analysed yet", href: `/results/${s.id}`,
    })),
  ];
  return { due, pending };
}

// Ticked task ids, per account, through a store (so the server render and the first client render agree)
const keyFor = (userId: string) => `speechmate:tasks-done:${userId}`;
const DONE_EVENT = "speechmate:tasks-done";
const subscribe = (cb: () => void) => { window.addEventListener(DONE_EVENT, cb); return () => window.removeEventListener(DONE_EVENT, cb); };

export default function TaskList({ userId, sessions, decks }: { userId: string; sessions: LiveSession[]; decks: DeckListItem[] }) {
  const raw = useSyncExternalStore(subscribe, () => { try { return localStorage.getItem(keyFor(userId)) ?? "[]"; } catch { return "[]"; } }, () => "[]");
  const done = useMemo(() => new Set<string>(JSON.parse(raw)), [raw]);
  const [tab, setTab] = useState<"due" | "pending">("due");
  const [all, setAll] = useState(false);
  // The completion animation: the row celebrates where it is, then sinks to the bottom and settles
  const [celebrating, setCelebrating] = useState<string | null>(null);
  const [settled, setSettled] = useState<string | null>(null);
  const { due, pending } = useMemo(() => buildTasks(sessions, decks), [sessions, decks]);

  // Open tasks first, ticked ones sink to the bottom (struck through)
  const ordered = [...due.filter((t) => !done.has(t.id)), ...due.filter((t) => done.has(t.id))];
  const open = due.length - due.filter((t) => done.has(t.id)).length;
  const shown = all ? ordered : ordered.slice(0, SHOW);

  const save = (next: Set<string>) => {
    // Keep only ids that still exist, so the list doesn't grow forever
    const ids = new Set(due.map((x) => x.id));
    try { localStorage.setItem(keyFor(userId), JSON.stringify([...next].filter((id) => ids.has(id)))); } catch { /* private mode */ }
    window.dispatchEvent(new Event(DONE_EVENT));
  };

  const toggle = (t: Task) => {
    if (celebrating) return;  // one celebration at a time
    if (done.has(t.id)) { const next = new Set(done); next.delete(t.id); save(next); return; }
    // Tick: pop, ripple, confetti and a flash in place (CELEBRATE_MS), then it sinks to the bottom
    setCelebrating(t.id);
    mascot("done", open <= 1 ? "All done for now. Brilliant!" : "Nice one! Ticked off.");
    setTimeout(() => {
      save(new Set(done).add(t.id));
      setCelebrating(null);
      setSettled(t.id);
      setTimeout(() => setSettled((id) => (id === t.id ? null : id)), 500);
    }, CELEBRATE_MS);
  };

  return (
    <section className="p-6 rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow-card)" }}>
      <div className="flex flex-wrap items-start gap-3 mb-4">
        <div className="mr-auto">
          <h2 className="text-base font-semibold" style={{ color: "var(--ink)" }}>My tasks</h2>
          <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
            {tab === "due" ? `${open} open · due today and late first` : "Still running"}
          </p>
        </div>
        <div role="tablist" aria-label="Tasks" className="inline-flex p-1 gap-1 rounded-full" style={{ background: "var(--surface-3)" }}>
          {([["due", "Due today & late", open], ["pending", "In progress", pending.length]] as const).map(([id, label, n]) => (
            <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors"
              style={{ background: tab === id ? "var(--surface)" : "transparent", color: tab === id ? "var(--ink)" : "var(--muted)", boxShadow: tab === id ? "var(--shadow-card)" : "none" }}>
              {label}
              <span className="tabular-nums px-1.5 rounded-full text-[10px]" style={{ background: tab === id ? "var(--surface-3)" : "var(--surface)" }}>{n}</span>
            </button>
          ))}
        </div>
      </div>

      {tab === "due" && (
        due.length === 0 ? <p className="text-sm py-4" style={{ color: "var(--muted)" }}>Nothing due. Finish a session and its drills appear here.</p> : (
          <>
            <ul className="divide-y divide-[var(--line-2)]">
              {shown.map((t) => {
                const party = celebrating === t.id;
                const isDone = done.has(t.id) || party;
                const d = dueLabel(t.due);
                const tag = TAGS[t.tag];
                return (
                  <li key={t.id} className={`row-in relative flex items-center gap-3 py-3 px-2 -mx-2 rounded-lg ${isDone ? "task-done" : ""} ${party ? "task-celebrate" : ""} ${settled === t.id ? "task-settle" : ""}`}>
                    <span className="relative flex-shrink-0">
                      <button onClick={() => toggle(t)} role="checkbox" aria-checked={isDone} aria-label={`${isDone ? "Untick" : "Tick off"}: ${t.title}`}
                        className={`w-6 h-6 rounded-full flex items-center justify-center transition-colors ${party ? "task-check-pop" : ""}`}
                        style={{ border: `2px solid ${isDone ? "var(--accent)" : "var(--line-strong)"}`, background: isDone ? "var(--accent)" : "transparent" }}>
                        {isDone && <Check className={`w-3.5 h-3.5 text-white ${party ? "upload-check" : ""}`} strokeWidth={3} />}
                      </button>
                      {party && (
                        <span aria-hidden className="pointer-events-none absolute inset-0 flex items-center justify-center">
                          <span className="task-ripple absolute inset-0 rounded-full" />
                          {CONFETTI.map(([dx, dy], i) => (
                            <span key={i} className="upload-burst" style={{ "--dx": `${dx}px`, "--dy": `${dy}px`, background: CONFETTI_COLORS[i % CONFETTI_COLORS.length] } as React.CSSProperties} />
                          ))}
                        </span>
                      )}
                    </span>
                    <Link href={t.href} className="flex-1 min-w-0">
                      <span className="task-title block text-sm font-semibold truncate" style={{ color: "var(--ink)" }}>{t.title}</span>
                      <span className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full font-medium" style={{ background: "var(--surface-3)", color: "var(--ink-2)" }}>
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: tag.dot }} />{tag.label}
                        </span>
                        <span style={{ color: d.late && !isDone ? "var(--bad)" : "var(--muted)" }}>{d.text}</span>
                      </span>
                    </Link>
                    {t.priority && !isDone && (
                      <span className="flex-shrink-0 inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md"
                        style={t.priority === "Urgent"
                          ? { background: "color-mix(in srgb, var(--bad) 12%, transparent)", color: "var(--bad)" }
                          : { background: "color-mix(in srgb, var(--warn) 14%, transparent)", color: "var(--warn)" }}>
                        {t.priority === "Urgent" && <Flag className="w-3 h-3" />}{t.priority}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
            {ordered.length > SHOW && (
              <button onClick={() => setAll((v) => !v)} className="mt-3 text-xs font-semibold" style={{ color: "var(--accent-ink)" }}>
                {all ? "Show fewer" : `All tasks (${ordered.length})`}
              </button>
            )}
          </>
        )
      )}

      {tab === "pending" && (
        pending.length === 0 ? <p className="text-sm py-4" style={{ color: "var(--muted)" }}>Nothing running right now.</p> : (
          <ul className="divide-y divide-[var(--line-2)]">
            {pending.map((p) => (
              <li key={p.id} className="row-in">
                <Link href={p.href} className="flex items-center gap-3 py-3">
                  <Loader2 className="w-5 h-5 flex-shrink-0 animate-spin" style={{ color: TAGS[p.tag].dot }} />
                  <span className="flex-1 min-w-0">
                    <span className="block text-sm font-semibold truncate" style={{ color: "var(--ink)" }}>{p.title}</span>
                    <span className="block text-xs mt-0.5" style={{ color: "var(--muted)" }}>{TAGS[p.tag].label} · {p.status}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )
      )}
    </section>
  );
}
