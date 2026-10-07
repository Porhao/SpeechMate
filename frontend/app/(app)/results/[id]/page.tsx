"use client";

// One session's results, kept simple:
//   1. the overall picture (score + a two-sentence summary)
//   2. four pillars: Voice · Language · Body language · Confidence (tap one for its metrics)
//   3. feedback on what you said (each interview / Q&A answer, or language tips)
//   4. the top three things to practise, each with the evidence it's based on
// Everything shown was measured in this session; anything that couldn't be is listed, not invented.

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, ArrowLeft, CheckCircle2, ChevronDown, Loader2, Play, RotateCcw } from "lucide-react";
import { liveService } from "@/services/live";
import { Button, Card, Dots, LinkButton, Notice, ScoreBar, StatusBadge, statusColor } from "@/components/ui/kit";
import { presentationService } from "@/services/presentation";
import type { ContentFeedback, FullAnalysisResult, LiveSession, Pillar, SlideFeedback } from "@/types";
import { formatDuration } from "@/utils/format";

const POLL_MS = 3000;
const TITLES: Record<string, string> = {
  Conversation: "Daily conversation", Interview: "Mock interview", Presentation: "Presentation Q&A", Pronunciation: "Pronunciation",
};
const STAGES = [
  "Transcribing what you said",
  "Measuring voice: pace, fluency, pronunciation, pitch, volume",
  "Reading body language from the video: eye contact, posture, gestures, expression",
  "Judging the content of your answers",
  "Writing your coaching plan",
];
const PILLAR_ORDER = ["voice", "language", "body", "confidence"] as const;

// "Practise this now": a short conversation on a topic that exercises the skill, with its goal on screen
const DRILLS: Record<string, [topic: string, goal: string]> = {
  fillers: ["Explain your favourite hobby to a friend who has never tried it", "Fillers: when you need a moment, pause silently instead of saying “um”. Aim for under 2 a minute."],
  pace: ["Describe a typical day for you, from morning to night", "Pace: keep a steady, comfortable speed, about 120–160 words a minute."],
  pauses: ["Tell the story of a memorable trip or day out", "Pauses: keep each sentence flowing; pause between ideas, not in the middle."],
  repetitions: ["Explain step by step how to cook a dish you know well", "Repetitions: slow down a little so each word comes out once."],
  pronunciation: ["Describe your hometown to a visitor", "Pronunciation: finish every word clearly, especially the endings."],
  eye_contact: ["Introduce yourself as if meeting a new classmate", "Eye contact: keep your eyes on the camera lens while you talk."],
  posture: ["Talk about your goals for this year", "Posture: sit tall, shoulders level, and stay still."],
  expression: ["Share some good news from your week", "Expression: relax your face and smile when it fits."],
  vocal_variety: ["Convince a friend to watch your favourite show", "Vocal variety: let your voice rise and fall to stress key words."],
  volume: ["Give directions from the nearest train station to your home", "Volume: speak as if to someone across the room."],
  hedging: ["Give your opinion: is social media good for young people?", "Directness: state your view plainly; skip “I think” and “maybe”."],
  length: ["Tell me about a project you are proud of", "Detail: give full answers with one concrete example each time."],
  response_time: ["Quick-fire questions about your favourite food, places and films", "Response time: start answering within 2 seconds, then think as you go."],
};
function drillHref(area: string | undefined): string | null {
  const d = area ? DRILLS[area] : undefined;
  return d ? `/session?mode=Conversation&topic=${encodeURIComponent(d[0])}&focus=${encodeURIComponent(d[1])}` : null;
}

function overallOf(a: FullAnalysisResult): number | null {
  if (a.communication_score.overall_score != null) return Math.round(a.communication_score.overall_score);
  const scores = PILLAR_ORDER.map((k) => a.pillars?.[k]?.score).filter((v): v is number => v != null);
  return scores.length ? Math.round(scores.reduce((x, y) => x + y, 0) / scores.length) : null;
}

function practiceAgainHref(s: LiveSession) {
  if (s.session_type === "Interview") return "/interview";
  if (s.session_type === "Presentation") return s.context?.deck_id ? `/presentations/${s.context.deck_id}` : "/presentations";
  return "/conversation";
}

// ── Pillar card ───────────────────────────────────────────────────────────────
function PillarCard({ pillar, open, onToggle }: { pillar: Pillar; open: boolean; onToggle: () => void }) {
  return (
    <div className="rounded-lg" style={{ background: "var(--surface)", border: `1px solid ${open ? "var(--accent-ink)" : "var(--line)"}`, boxShadow: "var(--shadow-card)" }}>
      <button onClick={onToggle} aria-expanded={open} className="w-full text-left p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>{pillar.label}</p>
          <ChevronDown className={`w-4 h-4 transition-transform ${open ? "rotate-180" : ""}`} style={{ color: "var(--muted)" }} />
        </div>
        <p className="font-display text-3xl mt-2 tabular-nums" style={{ color: pillar.score != null ? statusColor(pillar.status) : "var(--faint)" }}>
          {pillar.score != null ? Math.round(pillar.score) : "—"}
        </p>
        <div className="mt-2"><ScoreBar score={pillar.score} status={pillar.status} /></div>
        <p className="text-xs mt-2 leading-relaxed" style={{ color: "var(--muted)" }}>
          {pillar.metrics.length ? pillar.about : "Couldn't be measured this time (see the notes below)."}
        </p>
      </button>
    </div>
  );
}

function PillarDetail({ pillar }: { pillar: Pillar }) {
  return (
    <Card title={`${pillar.label}: what was measured`}>
      <div className="divide-y" style={{ borderColor: "var(--line-2)" }}>
        {pillar.metrics.map((m) => (
          <div key={m.key} className="py-3 grid sm:grid-cols-[180px_1fr_120px] gap-x-4 gap-y-1.5 items-center">
            <div>
              <p className="text-sm font-medium" style={{ color: "var(--ink)" }}>{m.label}</p>
              {m.hint && <p className="text-xs" style={{ color: "var(--muted)" }}>{m.hint}</p>}
            </div>
            <div>
              <ScoreBar score={m.score} status={m.status} />
              <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>Comfortable range: {m.range}</p>
            </div>
            <div className="sm:text-right">
              <p className="text-sm font-semibold tabular-nums" style={{ color: "var(--ink)" }}>{m.display}</p>
              <StatusBadge status={m.status} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── Confidence: which cues it was worked out from ─────────────────────────────
type Cue = { key: string; label: string; channel: string; weight: number; value: number; score: number };
const CUE_VALUE: Record<string, (v: number) => string> = {
  pace: (v) => `${Math.round(v)} words/min`, pauses: (v) => `${v.toFixed(0)} a minute`,
  repetitions: (v) => `${v.toFixed(1)} a minute`, blocks: (v) => `${v.toFixed(1)} a minute`,
  fillers: (v) => `${v.toFixed(1)} a minute`, response: (v) => `${v.toFixed(1)} s`,
  expression: (v) => `${Math.round(v)}/100`, relaxed: (v) => `tension ${Math.round(v)}/100`,
  posture: (v) => `${Math.round(v)}/100`, stability: (v) => `${Math.round(v)}/100`, eye_contact: (v) => `${Math.round(v)}%`,
};

function ConfidenceBreakdown({ conf }: { conf: { confidence_score: number; label: string; coverage?: number; cues?: Cue[] } }) {
  if (!conf.cues?.length) return null;
  const cues = [...conf.cues].sort((x, y) => x.score - y.score);  // weakest first: that's what to work on
  return (
    <Card title="How we worked out your confidence">
      <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--ink-2)" }}>
        Confidence can&apos;t be measured directly, so we score how confident you <i>come across</i>, from {conf.cues.length} things
        listeners notice. Each is scored 0–100, then combined by how much it matters.
        {conf.coverage != null && conf.coverage < 0.8 && <> Some cues couldn&apos;t be measured this time, so this is based on {Math.round(conf.coverage * 100)}% of the evidence.</>}
      </p>
      <div className="space-y-2.5">
        {cues.map((c) => (
          <div key={c.key} className="grid grid-cols-[1fr_auto] sm:grid-cols-[200px_1fr_130px] gap-x-4 gap-y-1 items-center">
            <p className="text-sm" style={{ color: "var(--ink)" }}>
              {c.label} <span className="text-xs" style={{ color: "var(--muted)" }}>· counts {Math.round(c.weight * 100)}%</span>
            </p>
            <p className="text-xs sm:text-right sm:order-last tabular-nums" style={{ color: "var(--muted)" }}>{CUE_VALUE[c.key]?.(c.value) ?? c.value}</p>
            <div className="col-span-2 sm:col-span-1">
              <ScoreBar score={c.score} status={c.score >= 75 ? "good" : c.score >= 50 ? "ok" : "work"} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── What you said ────────────────────────────────────────────────────────────
// ── Presentation talk: did what you said match each slide? ──────────────────────
const SLIDE_STATUS: Record<SlideFeedback["status"], { label: string; color: string }> = {
  covered: { label: "Covered well", color: "var(--ok)" },
  partly: { label: "Partly covered", color: "var(--warn)" },
  missed: { label: "Missed the point", color: "var(--bad)" },
  silent: { label: "Nothing said", color: "var(--bad)" },
  skipped: { label: "Not shown", color: "var(--muted)" },
};

function SlidesFeedbackCard({ fb, deckId }: { fb: Extract<ContentFeedback, { kind: "slides" }>; deckId?: string }) {
  const shown = fb.slides.filter((s) => s.status !== "skipped");
  const counts = (["covered", "partly", "missed", "silent", "skipped"] as const)
    .map((k) => [k, fb.slides.filter((s) => s.status === k).length] as const).filter(([, n]) => n > 0);
  return (
    <Card title="Did your talk match your slides?">
      <p className="text-sm leading-relaxed" style={{ color: "var(--ink-2)" }}>{fb.summary}</p>
      <p className="text-xs mt-2 flex flex-wrap gap-x-4 gap-y-1" style={{ color: "var(--muted)" }}>
        <span>{shown.length} of {fb.slides.length} slides presented · {formatDuration(Math.round(fb.total_sec))}</span>
        {counts.map(([k, n]) => (
          <span key={k} className="inline-flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: SLIDE_STATUS[k].color }} />{n} {SLIDE_STATUS[k].label.toLowerCase()}
          </span>
        ))}
      </p>
      <ol className="mt-5 space-y-4">
        {fb.slides.map((sl) => {
          const st = SLIDE_STATUS[sl.status];
          return (
            <li key={sl.slide_index} className="grid sm:grid-cols-[180px_1fr] gap-4 p-3 rounded-lg" style={{ border: "1px solid var(--line)" }}>
              {deckId ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={presentationService.slideImageUrl(deckId, sl.slide_index)} alt={`Slide ${sl.slide_index}`} loading="lazy"
                  className="w-full aspect-video object-contain rounded-md" style={{ background: "var(--surface-2)", opacity: sl.status === "skipped" ? 0.5 : 1 }} />
              ) : <span />}
              <div className="min-w-0 text-sm space-y-1.5">
                <p className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <b style={{ color: "var(--ink)" }}>Slide {sl.slide_index}{sl.title ? ` · ${sl.title}` : ""}</b>
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold" style={{ color: st.color }}>
                    <span className="w-2 h-2 rounded-full" style={{ background: st.color }} />{st.label}
                  </span>
                  {sl.status !== "skipped" && <span className="text-xs tabular-nums" style={{ color: "var(--muted)" }}>{formatDuration(Math.round(sl.seconds))} on screen</span>}
                  {sl.alignment != null && <Dots label="Match" value={sl.alignment} />}
                </p>
                {sl.key_point && <p style={{ color: "var(--ink-2)" }}><span style={{ color: "var(--muted)" }}>The slide&apos;s point:</span> {sl.key_point}</p>}
                {sl.said && (
                  <p className="pl-3 italic line-clamp-3" title={sl.said} style={{ borderLeft: "3px solid var(--line-strong)", color: "var(--ink-2)" }}>
                    You said: “{sl.said}”
                  </p>
                )}
                {sl.covered && <p style={{ color: "var(--ink-2)" }}><b style={{ color: "var(--ok)" }}>✓ Covered:</b> {sl.covered}</p>}
                {sl.missing && <p style={{ color: "var(--ink-2)" }}><b style={{ color: "var(--warn)" }}>Left out:</b> {sl.missing}</p>}
                {!sl.missing && sl.missed_terms.length > 0 && sl.status !== "covered" && (
                  <p style={{ color: "var(--ink-2)" }}><b style={{ color: "var(--warn)" }}>Didn&apos;t mention:</b> {sl.missed_terms.join(", ")}</p>
                )}
                {sl.tip && <p style={{ color: "var(--ink-2)" }}><b style={{ color: "var(--accent-ink)" }}>→ Next time:</b> {sl.tip}</p>}
                {sl.status === "silent" && <p style={{ color: "var(--muted)" }}>This slide was on screen but nothing was said about it.</p>}
                {sl.status === "skipped" && <p style={{ color: "var(--muted)" }}>You didn&apos;t show this slide.</p>}
              </div>
            </li>
          );
        })}
      </ol>
      {fb.source === "rules" && fb.slides.some((x) => x.said) && (
        <p className="text-xs mt-4" style={{ color: "var(--muted)" }}>
          Judged by matching the slide&apos;s key words because the AI model wasn&apos;t available; the AI gives a fuller judgement.
        </p>
      )}
    </Card>
  );
}

function AnswerFeedbackCard({ fb, sessionType }: { fb: ContentFeedback; sessionType: string }) {
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  if (fb.kind === "slides") return null;  // shown full width by SlidesFeedbackCard
  if (fb.kind === "conversation") {
    return (
      <Card title="Your language">
        <p className="text-sm leading-relaxed mb-4" style={{ color: "var(--ink-2)" }}>{fb.summary}</p>
        {fb.corrections.length > 0 && (
          <div className="space-y-3 mb-4">
            {fb.corrections.map((c, i) => (
              <div key={i} className="p-3 rounded-md" style={{ background: "var(--surface-2)" }}>
                <p className="text-sm" style={{ color: "var(--ink-2)" }}><span style={{ color: "var(--muted)" }}>You said:</span> “{c.said}”</p>
                <p className="text-sm font-medium mt-1" style={{ color: "var(--ink)" }}><span style={{ color: "var(--ok)" }}>Try saying:</span> “{c.better}”</p>
                {c.why && <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>Why: {c.why}</p>}
              </div>
            ))}
          </div>
        )}
        {fb.tips.length > 0 && (
          <ul className="space-y-1.5">
            {fb.tips.map((t, i) => (
              <li key={i} className="text-sm flex gap-2" style={{ color: "var(--ink-2)" }}>
                <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: "var(--accent-ink)" }} />{t}
              </li>
            ))}
          </ul>
        )}
      </Card>
    );
  }
  return (
    <Card title={sessionType === "Interview" ? "Your answers" : "Your Q&A answers"}>
      <p className="text-sm leading-relaxed mb-4" style={{ color: "var(--ink-2)" }}>{fb.summary}</p>
      <div className="space-y-3">
        {fb.answers.map((a, i) => (
          <div key={i} className="p-4 rounded-lg" style={{ border: "1px solid var(--line)" }}>
            <p className="text-sm font-semibold leading-snug" style={{ color: "var(--ink)" }}>Q{i + 1}. {a.question}</p>
            {a.answer && (
              <p className="text-sm mt-2 pl-3 italic leading-relaxed line-clamp-3" title={a.answer}
                style={{ borderLeft: "3px solid var(--line-strong)", color: "var(--ink-2)" }}>
                You said: “{a.answer}”
              </p>
            )}
            <div className="flex flex-wrap gap-x-5 gap-y-1 mt-3">
              <Dots label="Answered the question" value={a.relevance} />
              <Dots label="Easy to follow" value={a.structure} />
              <Dots label="Real details" value={a.specificity} />
            </div>
            {a.went_well && <p className="text-sm mt-3" style={{ color: "var(--ink-2)" }}><b style={{ color: "var(--ok)" }}>✓ Good:</b> {a.went_well}</p>}
            <p className="text-sm mt-1.5" style={{ color: "var(--ink-2)" }}><b style={{ color: "var(--warn)" }}>→ Next time:</b> {a.improve}</p>
            <button onClick={() => setOpenIdx(openIdx === i ? null : i)} className="flex items-center gap-1 text-xs font-semibold mt-3" style={{ color: "var(--accent-ink)" }}>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${openIdx === i ? "rotate-180" : ""}`} />
              {openIdx === i ? "Hide" : "See"} a stronger version of your answer
            </button>
            {openIdx === i && (
              <p className="text-sm mt-2 p-3 rounded-md leading-relaxed" style={{ background: "var(--surface-2)", color: "var(--ink-3)" }}>{a.stronger_answer}</p>
            )}
          </div>
        ))}
      </div>
      {fb.source === "rules" && (
        <p className="text-xs mt-3" style={{ color: "var(--muted)" }}>
          Scored with simple rules because the AI model wasn&apos;t available; the AI gives more specific feedback.
        </p>
      )}
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function ResultsPage() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<LiveSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openPillar, setOpenPillar] = useState<string | null>(null);
  const [showTranscript, setShowTranscript] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const load = useCallback(async () => {
    try { setSession(await liveService.get(id)); setError(null); }
    catch (e) { setError(e instanceof Error ? e.message : "Couldn't load this session"); }
  }, [id]);

  useEffect(() => {
    liveService.get(id).then(setSession).catch((e) => setError(e instanceof Error ? e.message : "Couldn't load this session"));
  }, [id]);
  const analyzing = session?.status === "analyzing";
  useEffect(() => {
    if (!analyzing) return;
    const poll = setInterval(load, POLL_MS);
    const tick = setInterval(() => setElapsed((v) => v + 1), 1000);
    return () => { clearInterval(poll); clearInterval(tick); };
  }, [analyzing, load]);

  const retry = async () => {
    setRetrying(true);
    try { await liveService.startAnalysis(id); setElapsed(0); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Couldn't restart the analysis"); }
    finally { setRetrying(false); }
  };

  if (error && !session) {
    return (
      <div className="px-4 py-16 max-w-xl mx-auto space-y-4">
        <Notice tone="bad">{error}</Notice>
        <LinkButton href="/progress" variant="secondary">Back to your sessions</LinkButton>
      </div>
    );
  }
  if (!session) {
    return <div className="flex justify-center py-24"><Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--muted)" }} /></div>;
  }

  const a = session.analysis;
  const title = session.context?.kind === "talk" ? "Presentation" : TITLES[session.session_type] ?? session.session_type;
  const subtitle = session.session_type === "Interview" && session.context?.setup
    ? `${session.context.setup.position}${session.context.setup.company ? ` · ${session.context.setup.company}` : ""}`
    : session.session_type === "Presentation" ? session.context?.deck_title
    : session.context?.topic;
  const overall = a ? overallOf(a) : null;
  const pillars = a?.pillars ? PILLAR_ORDER.map((k) => a.pillars![k]) : [];
  const opened = pillars.find((p) => p.key === openPillar);
  const stage = Math.min(STAGES.length - 1, Math.floor(elapsed / 12));

  return (
    <div className="px-4 sm:px-6 py-8 max-w-[1100px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/progress" className="inline-flex items-center gap-1 text-xs font-semibold mb-3" style={{ color: "var(--muted)" }}>
            <ArrowLeft className="w-3.5 h-3.5" /> All sessions
          </Link>
          <h1 className="font-display text-3xl" style={{ color: "var(--ink)" }}>{title}</h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            {subtitle ? `${subtitle} · ` : ""}{formatDuration(Math.round(a?.duration_sec ?? session.duration_sec))} ·{" "}
            {new Date(session.created_at).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" })}
          </p>
        </div>
        <LinkButton href={practiceAgainHref(session)}><RotateCcw className="w-4 h-4" /> Practise again</LinkButton>
      </div>

      {/* Still analysing */}
      {(analyzing || session.status === "active") && (
        <Card>
          {session.status === "active" ? (
            <div className="space-y-3">
              <p className="text-sm" style={{ color: "var(--ink-2)" }}>
                {session.has_recording ? "The recording was saved but the analysis hasn't started." : "This session has no recording yet, so it can't be analysed."}
              </p>
              {session.has_recording && <Button onClick={retry} disabled={retrying}>Analyse now</Button>}
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--accent-ink)" }} />
                <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>Analysing your session… {formatDuration(elapsed)}</p>
              </div>
              <ol className="space-y-2">
                {STAGES.map((s, i) => (
                  <li key={s} className="text-sm flex items-center gap-2" style={{ color: i <= stage ? "var(--ink-2)" : "var(--faint)" }}>
                    <span className="w-1.5 h-1.5" style={{ background: i < stage ? "var(--ok)" : i === stage ? "var(--accent-ink)" : "var(--line-strong)" }} />
                    {s}
                  </li>
                ))}
              </ol>
              <p className="text-xs mt-4" style={{ color: "var(--muted)" }}>
                On a CPU this takes one to a few minutes. You can leave this page: the bell at the top tells you when it&apos;s ready.
              </p>
            </div>
          )}
        </Card>
      )}

      {session.status === "failed" && (
        <Card>
          <Notice tone="bad">{session.error_detail ?? "The analysis failed."}</Notice>
          {session.has_recording && <Button className="mt-4" onClick={retry} disabled={retrying}>Try the analysis again</Button>}
        </Card>
      )}

      {a && session.status === "complete" && (
        <>
          {/* 1. Overall */}
          <Card>
            <div className="grid sm:grid-cols-[160px_1fr] gap-6 items-center">
              <div className="text-center sm:text-left">
                <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--muted)" }}>Overall</p>
                <p className="font-display text-6xl tabular-nums leading-none mt-1" style={{ color: "var(--ink)" }}>{overall ?? "—"}</p>
                {a.communication_score.grade && <p className="text-sm mt-1 font-semibold" style={{ color: "var(--accent-ink)" }}>{a.communication_score.grade}</p>}
              </div>
              <div>
                <p className="text-[15px] leading-relaxed" style={{ color: "var(--ink-2)" }}>
                  {a.recommendations.summary || "Here's how this session went."}
                </p>
                {a.communication_score.strengths.length > 0 && (
                  <p className="text-sm mt-2" style={{ color: "var(--ink-2)" }}>
                    <b style={{ color: "var(--ok)" }}>Strengths:</b> {a.communication_score.strengths.join(", ")}
                  </p>
                )}
              </div>
            </div>
          </Card>

          {/* The single most useful thing to do next, impossible to miss */}
          {a.recommendations.exercises[0] && (() => {
            const e = a.recommendations.exercises[0];
            return (
              <div className="clay rounded-xl p-6 sm:p-7" style={{ background: "var(--peach)", color: "#0A0A0A" }}>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] opacity-70">Your #1 focus for next time</p>
                <p className="font-display text-2xl sm:text-3xl mt-1 leading-tight">{e.title}</p>
                {e.evidence && <p className="text-sm mt-2 leading-relaxed opacity-85">{e.evidence}</p>}
                <p className="text-sm mt-4 p-4 rounded-lg leading-relaxed" style={{ background: "#FFFAF0", color: "#1A1A1A" }}>
                  <b>Try this ({e.daily_minutes} min a day):</b> {e.description}
                </p>
                <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
                  {drillHref(e.area) && (
                    <LinkButton href={drillHref(e.area)!}><Play className="w-4 h-4" /> Practise this now</LinkButton>
                  )}
                  <p className="text-sm font-semibold">Next time, aim for: {e.metric_target}</p>
                </div>
              </div>
            );
          })()}

          {/* 2. Pillars */}
          {pillars.length > 0 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {pillars.map((p) => (
                  <PillarCard key={p.key} pillar={p} open={openPillar === p.key}
                    onToggle={() => setOpenPillar(openPillar === p.key ? null : p.key)} />
                ))}
              </div>
              {opened && opened.metrics.length > 0 && <PillarDetail pillar={opened} />}
              {!opened && <p className="text-xs" style={{ color: "var(--muted)" }}>Tap a pillar to see each metric, your value and the comfortable range.</p>}
            </div>
          )}

          {(() => {
            const conf = (a.details as { confidence?: Parameters<typeof ConfidenceBreakdown>[0]["conf"] | null }).confidence;
            return conf ? <ConfidenceBreakdown conf={conf} /> : null;
          })()}

          {a.content_feedback?.kind === "slides" && <SlidesFeedbackCard fb={a.content_feedback} deckId={session.context?.deck_id} />}

          <div className="grid lg:grid-cols-2 gap-6 items-start">
            {/* 3. What you said */}
            {a.content_feedback?.kind === "slides" ? null : a.content_feedback ? (
              <AnswerFeedbackCard fb={a.content_feedback} sessionType={session.session_type} />
            ) : (
              <Card title="What you said">
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  {a.transcript ? "No question-and-answer turns were recorded for this session." : "No transcript was available, so the content couldn't be judged."}
                </p>
              </Card>
            )}

            {/* 4. Practise next */}
            <Card title={a.recommendations.exercises.length > 1 ? "Also worth practising" : "What to practise next"}>
              {a.recommendations.exercises.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--ink-2)" }}>Nothing stood out as needing work. Keep practising to stay sharp.</p>
              ) : a.recommendations.exercises.length === 1 ? (
                <p className="text-sm" style={{ color: "var(--ink-2)" }}>Just the one focus above this time. Practise it, then come back and compare.</p>
              ) : (
                <ol className="space-y-5">
                  {a.recommendations.exercises.slice(1).map((e, i) => (
                    <li key={i}>
                      <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>{i + 2}. {e.title}</p>
                      {e.evidence && <p className="text-sm mt-1" style={{ color: "var(--ink-2)" }}><span style={{ color: "var(--muted)" }}>What we noticed: </span>{e.evidence}</p>}
                      {e.why && <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>Why it matters: {e.why}</p>}
                      <p className="text-sm mt-2 p-3 rounded-md leading-relaxed" style={{ background: "var(--surface-2)", color: "var(--ink-3)" }}>
                        <b>Try this ({e.daily_minutes} min a day):</b> {e.description}
                      </p>
                      <p className="text-xs mt-1.5 font-semibold" style={{ color: "var(--accent-ink)" }}>Next time, aim for: {e.metric_target}</p>
                      {drillHref(e.area) && (
                        <Link href={drillHref(e.area)!} className="inline-flex items-center gap-1 text-xs font-semibold mt-2" style={{ color: "var(--accent-ink)" }}>
                          <Play className="w-3.5 h-3.5" /> Practise this now (3 min)
                        </Link>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          </div>

          {/* Language mix (Malaysian speakers) */}
          {a.language && (a.language.is_code_switching || a.language.manglish_particles.length > 0 || a.language.malay_ratio > 0) && (
            <Card title="Language mix">
              <p className="text-sm" style={{ color: "var(--ink-2)" }}>
                {Math.round(a.language.english_ratio * 100)}% English · {Math.round(a.language.malay_ratio * 100)}% Bahasa Melayu
                {a.language.manglish_particles.length > 0 && <> · particles: {a.language.manglish_particles.join(", ")}</>}
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
                Mixing languages is normal in Malaysia. Pronunciation scoring allows for the Malaysian English accent.
              </p>
            </Card>
          )}

          {/* Transcript + notes */}
          {a.transcript && (
            <div>
              <button onClick={() => setShowTranscript((v) => !v)} className="flex items-center gap-1 text-sm font-semibold" style={{ color: "var(--accent-ink)" }}>
                <ChevronDown className={`w-4 h-4 transition-transform ${showTranscript ? "rotate-180" : ""}`} />
                {showTranscript ? "Hide" : "Show"} transcript
              </button>
              {showTranscript && (
                <div className="mt-3 p-4 space-y-2 text-sm leading-relaxed" style={{ background: "var(--surface)", border: "1px solid var(--line)", color: "var(--ink-3)" }}>
                  {session.turns?.length
                    ? session.turns.map((t, i) => (
                        <p key={i}><b style={{ color: t.role === "user" ? "var(--accent-ink)" : "var(--muted)" }}>{t.role === "user" ? "You" : "AI"}:</b> {t.text}</p>
                      ))
                    : <p className="whitespace-pre-wrap">{a.transcript}</p>}
                </div>
              )}
            </div>
          )}
          {session.warnings.length > 0 && (
            <details className="text-sm" style={{ color: "var(--muted)" }}>
              <summary className="cursor-pointer flex items-center gap-1.5 font-semibold">
                <AlertTriangle className="w-4 h-4" /> {session.warnings.length} note{session.warnings.length === 1 ? "" : "s"} about this analysis
              </summary>
              <ul className="mt-2 space-y-1 list-disc pl-5 text-xs">
                {session.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </details>
          )}
        </>
      )}
    </div>
  );
}
