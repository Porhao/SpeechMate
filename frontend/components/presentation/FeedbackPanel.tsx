"use client";

import { useState } from "react";
import { ThumbsUp, Eye, Zap, Lightbulb, Users, AlertTriangle, ChevronDown } from "lucide-react";
import type { PracticeRun } from "@/types";
import { formatDuration } from "@/utils/format";
import { inkOf } from "@/lib/utils";

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl px-3 py-2.5" style={{ background: "var(--surface-2)", border: "1px solid var(--line)" }}>
      <p className="text-[10px] uppercase tracking-wide font-semibold" style={{ color: "var(--faint)" }}>{label}</p>
      <p className="text-lg font-bold tabular-nums" style={{ color: "var(--ink)" }}>{value}</p>
      {hint && <p className="text-[11px]" style={{ color: "var(--muted)" }}>{hint}</p>}
    </div>
  );
}

function Dots({ score }: { score: number }) {
  return (
    <span className="inline-flex gap-0.5" aria-label={`${score} out of 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className="w-2 h-2 rounded-full" style={{ background: i <= score ? "#23345C" : "var(--line)" }} />
      ))}
    </span>
  );
}

const secs = (n: number) => formatDuration(Math.round(n));

export default function FeedbackPanel({ run }: { run: PracticeRun }) {
  const [showTranscript, setShowTranscript] = useState(false);
  const m = run.metrics;
  const fb = run.feedback;
  const aud = run.audience_feedback;

  return (
    <div className="space-y-4">
      {run.warnings.length > 0 && (
        <div className="text-xs px-3 py-2 rounded-lg space-y-1" style={{ background: "rgba(138,90,34,0.07)", border: "1px solid rgba(138,90,34,0.2)", color: "#6B4419" }}>
          {run.warnings.map((w, i) => (
            <p key={i} className="flex gap-1.5"><AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-px" />{w}</p>
          ))}
        </div>
      )}

      {fb && (
        <div className="rounded-xl p-4" style={{ background: "rgba(63,107,76,0.07)", border: "1px solid rgba(63,107,76,0.22)" }}>
          <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-1" style={{ color: "var(--ok)" }}>
            <ThumbsUp className="w-3.5 h-3.5" /> What went well
          </p>
          <p className="text-sm leading-relaxed" style={{ color: "var(--ink-3)" }}>{fb.encouragement}</p>
        </div>
      )}

      {fb?.observations.map((o, i) => (
        <div key={i} className="glass-card rounded-xl p-4 space-y-3">
          {o.slide_index != null && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-md" style={{ background: "#23345C14", color: "var(--accent-ink)" }}>
              Slide {o.slide_index}
            </span>
          )}
          {([
            ["Observation", o.observation, Eye, "#23345C"],
            ["Impact", o.impact, Zap, "#8A5A22"],
            ["Suggestion", o.suggestion, Lightbulb, "#3F6B4C"],
          ] as const).map(([label, text, Icon, color]) => (
            <div key={label} className="flex gap-2.5">
              <Icon className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: inkOf(color) }} />
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wide" style={{ color: inkOf(color) }}>{label}</p>
                <p className="text-sm leading-relaxed" style={{ color: "var(--ink-3)" }}>{text}</p>
              </div>
            </div>
          ))}
        </div>
      ))}

      {m && (
        <div>
          <p className="text-xs font-semibold mb-2" style={{ color: "var(--muted)" }}>Delivery metrics</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <Tile label="Duration" value={secs(m.duration_sec)} hint={m.ideal_duration_sec ? `ideal ${secs(m.ideal_duration_sec)}` : undefined} />
            {m.wpm != null && <Tile label="Pace" value={`${Math.round(m.wpm)} wpm`} hint={m.ideal_wpm ? `ideal ${Math.round(m.ideal_wpm)} wpm` : undefined} />}
            <Tile label="Pauses" value={String(m.pause_count)} hint={`longest ${m.longest_pause_sec.toFixed(1)}s`} />
            {m.filler_word_count != null && (
              <Tile label="Filler words" value={String(m.filler_word_count)}
                hint={m.fillers_per_minute != null ? `${m.fillers_per_minute}/min` : undefined} />
            )}
            {m.script_coverage != null && (
              <Tile label="Key-term coverage" value={`${Math.round(m.script_coverage * 100)}%`} />
            )}
          </div>
          {m.filler_words && Object.keys(m.filler_words).length > 0 && (
            <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
              Fillers: {Object.entries(m.filler_words).map(([w, n]) => `“${w}” ×${n}`).join(", ")}
            </p>
          )}
          {m.missed_key_terms && m.missed_key_terms.length > 0 && (
            <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>Missed key terms: {m.missed_key_terms.join(", ")}</p>
          )}
          {m.long_pauses.length > 0 && (
            <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
              Long pauses at: {m.long_pauses.map((p) => `${secs(p.at_sec)} (${p.duration_sec}s)`).join(", ")}
            </p>
          )}
        </div>
      )}

      {m?.slide_coverage && m.slide_coverage.length > 0 && (
        <div>
          <p className="text-xs font-semibold mb-2" style={{ color: "var(--muted)" }}>Key point per slide</p>
          <ul className="space-y-1.5">
            {m.slide_coverage.map((c) => {
              const color = c.status === "covered" ? "var(--ok)" : c.status === "partly" ? "var(--warn)" : "var(--bad)";
              return (
                <li key={c.slide_index} className="flex items-start gap-3 text-sm">
                  <span className="w-14 flex-shrink-0 text-xs font-semibold pt-0.5" style={{ color: "var(--muted)" }}>Slide {c.slide_index}</span>
                  <span className="flex-1 min-w-0" style={{ color: "var(--ink-3)" }}>
                    {c.key_point ?? "—"}
                    {c.status !== "covered" && c.missed.length > 0 && (
                      <span className="block text-xs" style={{ color: "var(--muted)" }}>Not said: {c.missed.slice(0, 4).join(", ")}</span>
                    )}
                  </span>
                  <span className="text-xs font-semibold flex-shrink-0" style={{ color }}>
                    {c.status === "covered" ? "Covered" : c.status === "partly" ? "Partly" : "Missed"}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {aud && (
        <div className="glass-card rounded-xl p-4 space-y-2">
          <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide" style={{ color: "#5A5470" }}>
            <Users className="w-3.5 h-3.5" /> Audience view · {aud.audience_profile}
          </p>
          {aud.overall_impression && <p className="text-sm italic" style={{ color: "var(--ink-3)" }}>&ldquo;{aud.overall_impression}&rdquo;</p>}
          <div className="flex gap-5 text-xs" style={{ color: "var(--ink-2)" }}>
            <span className="flex items-center gap-2">Clarity <Dots score={aud.clarity_score} /></span>
            <span className="flex items-center gap-2">Engagement <Dots score={aud.engagement_score} /></span>
          </div>
          <p className="text-sm" style={{ color: "var(--ink-3)" }}><b>Key takeaway:</b> {aud.key_takeaway}</p>
          {[
            ["What held my attention", aud.engaging_moments],
            ["Where I got lost", aud.confusing_moments],
            ["What I'd ask you", aud.questions_i_would_ask],
          ].map(([title, items]) =>
            items && (items as string[]).length > 0 ? (
              <div key={title as string}>
                <p className="text-xs font-semibold" style={{ color: "var(--muted)" }}>{title as string}</p>
                <ul className="list-disc pl-5 text-sm" style={{ color: "var(--ink-3)" }}>
                  {(items as string[]).map((x, i) => <li key={i}>{x}</li>)}
                </ul>
              </div>
            ) : null,
          )}
        </div>
      )}

      {run.transcript && (
        <div>
          <button onClick={() => setShowTranscript((v) => !v)} className="flex items-center gap-1 text-xs font-semibold" style={{ color: "var(--muted)" }}>
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showTranscript ? "rotate-180" : ""}`} />
            {showTranscript ? "Hide" : "Show"} transcript
          </button>
          {showTranscript && (
            <p className="mt-2 text-sm leading-relaxed whitespace-pre-wrap p-3 rounded-lg" style={{ background: "var(--surface-2)", color: "var(--ink-3)" }}>
              {run.transcript}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
