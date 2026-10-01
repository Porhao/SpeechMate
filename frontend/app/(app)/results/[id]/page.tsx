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
import { AlertTriangle, ArrowLeft, CheckCircle2, ChevronDown, Loader2, RotateCcw } from "lucide-react";
import { liveService } from "@/services/live";
import { Button, Card, Dots, LinkButton, Notice, ScoreBar, StatusBadge, statusColor } from "@/components/ui/kit";
import type { ContentFeedback, FullAnalysisResult, LiveSession, Pillar } from "@/types";
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
    <div style={{ background: "var(--surface)", border: `1px solid ${open ? "var(--accent-ink)" : "var(--line)"}` }}>
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

// ── What you said ────────────────────────────────────────────────────────────
function AnswerFeedbackCard({ fb, sessionType }: { fb: ContentFeedback; sessionType: string }) {
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  if (fb.kind === "conversation") {
    return (
      <Card title="Your language">
        <p className="text-sm leading-relaxed mb-4" style={{ color: "var(--ink-2)" }}>{fb.summary}</p>
        {fb.corrections.length > 0 && (
          <div className="space-y-3 mb-4">
            {fb.corrections.map((c, i) => (
              <div key={i} className="p-3" style={{ background: "var(--surface-2)" }}>
                <p className="text-sm" style={{ color: "var(--ink-2)" }}><span style={{ color: "var(--muted)" }}>You said:</span> “{c.said}”</p>
                <p className="text-sm font-medium mt-1" style={{ color: "var(--ink)" }}><span style={{ color: "var(--ok)" }}>More natural:</span> “{c.better}”</p>
                <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>{c.why}</p>
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
          <div key={i} className="p-4" style={{ border: "1px solid var(--line)" }}>
            <p className="text-sm font-semibold leading-snug" style={{ color: "var(--ink)" }}>Q{i + 1}. {a.question}</p>
            <div className="flex flex-wrap gap-x-5 gap-y-1 mt-2">
              <Dots label="On topic" value={a.relevance} />
              <Dots label="Structure" value={a.structure} />
              <Dots label="Specific" value={a.specificity} />
            </div>
            <p className="text-sm mt-3" style={{ color: "var(--ink-2)" }}><b style={{ color: "var(--ok)" }}>Went well:</b> {a.went_well}</p>
            <p className="text-sm mt-1" style={{ color: "var(--ink-2)" }}><b style={{ color: "var(--warn)" }}>Improve:</b> {a.improve}</p>
            <button onClick={() => setOpenIdx(openIdx === i ? null : i)} className="flex items-center gap-1 text-xs font-semibold mt-2" style={{ color: "var(--accent-ink)" }}>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${openIdx === i ? "rotate-180" : ""}`} />
              {openIdx === i ? "Hide" : "Show"} a stronger answer
            </button>
            {openIdx === i && (
              <p className="text-sm mt-2 p-3 leading-relaxed" style={{ background: "var(--surface-2)", color: "var(--ink-3)" }}>{a.stronger_answer}</p>
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
  const title = TITLES[session.session_type] ?? session.session_type;
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

          <div className="grid lg:grid-cols-2 gap-6 items-start">
            {/* 3. What you said */}
            {a.content_feedback ? (
              <AnswerFeedbackCard fb={a.content_feedback} sessionType={session.session_type} />
            ) : (
              <Card title="What you said">
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  {a.transcript ? "No question-and-answer turns were recorded for this session." : "No transcript was available, so the content couldn't be judged."}
                </p>
              </Card>
            )}

            {/* 4. Practise next */}
            <Card title="Practise next">
              {a.recommendations.exercises.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--ink-2)" }}>Nothing stood out as needing work. Keep practising to stay sharp.</p>
              ) : (
                <ol className="space-y-5">
                  {a.recommendations.exercises.map((e, i) => (
                    <li key={i}>
                      <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>{i + 1}. {e.title}</p>
                      {e.evidence && <p className="text-sm mt-1" style={{ color: "var(--ink-2)" }}><span style={{ color: "var(--muted)" }}>Measured: </span>{e.evidence}</p>}
                      {e.why && <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>{e.why}</p>}
                      <p className="text-sm mt-2 p-3 leading-relaxed" style={{ background: "var(--surface-2)", color: "var(--ink-3)" }}>
                        <b>Drill ({e.daily_minutes} min):</b> {e.description}
                      </p>
                      <p className="text-xs mt-1.5 font-semibold" style={{ color: "var(--accent-ink)" }}>Target: {e.metric_target}</p>
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
