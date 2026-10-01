"use client";

// Deck insights, computed before narration: what the talk says, how it's built,
// what each slide must land, and what to fix or prepare before rehearsing.

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { DeckInsights } from "@/types";

function Label({ children }: { children: React.ReactNode }) {
  return <p className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-[var(--muted)]">{children}</p>;
}

export default function DeckInsightsPanel({ insights, defaultOpen = true }: { insights: DeckInsights; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const { stats } = insights;
  const [lo, hi] = stats.estimated_minutes;

  return (
    <section className="glass-card">
      <button onClick={() => setOpen((v) => !v)} className="w-full flex items-center justify-between gap-3 px-5 py-4 text-left">
        <div>
          <h2 className="text-sm font-semibold text-[var(--ink)]">Deck insights</h2>
          <p className="text-xs text-[var(--muted)] mt-0.5">
            Read this before you practise — {insights.source === "llm" ? "analysed by the AI coach" : "outline from the slide text"}
          </p>
        </div>
        <ChevronDown className={`w-4 h-4 text-[var(--muted)] transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-5" style={{ borderTop: "1px solid var(--line)" }}>
          <div className="pt-4">
            <Label>Main message</Label>
            <p className="font-display text-lg leading-snug text-[var(--ink)]">{insights.main_message}</p>
            <p className="text-sm leading-relaxed text-[var(--ink-2)] mt-2">{insights.summary}</p>
            {insights.audience && <p className="text-xs text-[var(--muted)] mt-2">Audience fit: {insights.audience}</p>}
          </div>

          {/* Measured stats */}
          <dl className="grid grid-cols-2 sm:grid-cols-4" style={{ border: "1px solid var(--line)" }}>
            {[
              ["Slides", String(stats.slide_count)],
              ["Talk length", `${lo}–${hi} min`],
              ["Words on slides", String(stats.total_words)],
              ["Text-heavy slides", stats.text_heavy_slides.length ? stats.text_heavy_slides.join(", ") : "None"],
            ].map(([k, v], i) => (
              <div key={k} className="px-3 py-2.5" style={{ borderLeft: i ? "1px solid var(--line)" : undefined }}>
                <dt className="text-[10px] uppercase tracking-wide text-[var(--muted)]">{k}</dt>
                <dd className="text-sm font-semibold text-[var(--ink)] mt-0.5">{v}</dd>
              </div>
            ))}
          </dl>

          {/* Structure with each slide's key point */}
          <div>
            <Label>Structure and key points</Label>
            <ol className="space-y-3">
              {insights.structure.map((section) => (
                <li key={section.section}>
                  <p className="text-xs font-semibold text-[var(--ink)]">{section.section}</p>
                  <ul className="mt-1 space-y-1">
                    {section.slides.map((n) => {
                      const point = insights.slides.find((s) => s.slide_index === n)?.key_point;
                      return (
                        <li key={n} className="flex gap-3 text-sm">
                          <span className="w-14 flex-shrink-0 text-xs tabular-nums text-[var(--muted)] pt-0.5">Slide {n}</span>
                          <span className="text-[var(--ink-2)]">{point ?? "—"}</span>
                        </li>
                      );
                    })}
                  </ul>
                </li>
              ))}
            </ol>
          </div>

          {insights.suggestions.length > 0 && (
            <div>
              <Label>Fix before you rehearse</Label>
              <ul className="space-y-2">
                {insights.suggestions.map((s, i) => (
                  <li key={i} className="text-sm pl-3" style={{ borderLeft: "2px solid var(--warn)" }}>
                    <p className="text-[var(--ink)]">
                      {s.slide_index ? <span className="font-semibold">Slide {s.slide_index}: </span> : null}
                      {s.issue}
                    </p>
                    <p className="text-[var(--ink-2)]">{s.suggestion}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid sm:grid-cols-2 gap-5">
            {insights.strengths.length > 0 && (
              <div>
                <Label>Strengths</Label>
                <ul className="list-disc pl-5 text-sm text-[var(--ink-2)] space-y-1">
                  {insights.strengths.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </div>
            )}
            {insights.likely_questions.length > 0 && (
              <div>
                <Label>Questions to prepare for</Label>
                <ul className="list-disc pl-5 text-sm text-[var(--ink-2)] space-y-1">
                  {insights.likely_questions.map((q, i) => <li key={i}>{q}</li>)}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
