"use client";

// Reference matrix: exactly how every score in the app is measured, and how each
// component is evaluated for the project. Kept in sync with the backend code paths
// listed in the "Source" column.

import { useState } from "react";

type Row = { metric: string; meaning: string; method: string; unit: string; range: string; source: string };

const LIVE: Row[] = [
  { metric: "Transcript", meaning: "What you said, word for word (fillers kept)",
    method: "Mesolitica Malaysian Whisper large-v3-turbo via faster-whisper (int8, 8 CPU threads, beam 5, “ms” token, voice-activity filter). Fallback: OpenAI Whisper.",
    unit: "text + word timings", range: "Benchmark: 7.9% WER (Malay 7.4%, English 4.0%, Manglish 17.0%)", source: "live/asr.py" },
  { metric: "Speaking rate", meaning: "How fast you talk",
    method: "Words ÷ recording length × 60", unit: "words/min", range: "120–160 comfortable · flagged > 165 or < 110", source: "live/speech.py" },
  { metric: "Articulation rate", meaning: "Pace while actually speaking",
    method: "Words ÷ speaking time (pauses removed) × 60", unit: "words/min", range: "—", source: "live/speech.py" },
  { metric: "Pauses", meaning: "Silences between words",
    method: "Gaps > 0.25 s between word timestamps; if timings are missing, ffmpeg silencedetect at −35 dB on the audio. Start/end silence ignored.",
    unit: "count, seconds", range: "Mid-sentence silence ≥ 1.2 s counts as a block", source: "live/speech.py" },
  { metric: "Fluency score", meaning: "Pace and continuity combined",
    method: "100 − |wpm − 135| × 0.5 − min(2 × pauses, 30)", unit: "0–100", range: "≥ 80 Excellent · ≥ 65 Good · ≥ 50 Fair", source: "live/speech.py" },
  { metric: "Filler words", meaning: "um, uh, like, you know… and BM fillers (err, macam, sebenarnya, lah…)",
    method: "Whole-word match against an English + Bahasa Melayu filler lexicon on the transcript", unit: "count, per minute",
    range: "< 3/min fine · flagged ≥ 3/min", source: "live/speech.py" },
  { metric: "Stuttering", meaning: "Repetitions, blocks, prolongations",
    method: "Repetition: same word twice within 0.6 s. Block: mid-sentence silence ≥ 1.2 s. Prolongation: steady-energy voiced sound ≥ 0.35 s (librosa RMS + zero-crossing rate). Score = 8 × events.",
    unit: "0–100 (higher = more)", range: "0 None · < 25 Mild · < 50 Moderate · ≥ 50 Severe", source: "live/speech.py" },
  { metric: "Pronunciation", meaning: "How clearly words were articulated",
    method: "Wav2Vec2 (facebook/wav2vec2-base-960h) CTC confidence averaged over each word's span; words < 75 marked unclear; +5% Malaysian-English allowance",
    unit: "0–100", range: "Flagged < 80 or ≥ 3 unclear words", source: "live/pronunciation.py" },
  { metric: "Language mix", meaning: "English vs Bahasa Melayu, Manglish particles",
    method: "Word ratio against a ~190-word BM/Manglish lexicon; code-switching when both languages ≥ 15%", unit: "ratios", range: "Informational, not scored", source: "live/language.py" },
  { metric: "Eye contact", meaning: "How often you look at the lens",
    method: "MediaPipe Face Mesh iris position on 60 sampled frames → camera / left / right / down; score = % of frames toward the camera",
    unit: "0–100", range: "Flagged < 70", source: "live/vision.py" },
  { metric: "Posture", meaning: "Upright, level, steady",
    method: "MediaPipe Pose: head tilt from the ear line, shoulder height difference, torso movement across frames; score = mean of the three",
    unit: "0–100", range: "Flagged < 75", source: "live/vision.py" },
  { metric: "Facial expression", meaning: "Dominant emotion and tension",
    method: "Face crop (MediaPipe) → ViT expression classifier (trpakov/vit-face-expression) on ~24 frames; tension = share of fearful + angry + sad",
    unit: "label, 0–100", range: "Tension flagged ≥ 30", source: "live/vision.py" },
  { metric: "Lighting & contrast", meaning: "How well you're lit on camera",
    method: "In the browser, once a second: face-region brightness (MediaPipe face box), whole-frame brightness, face vs. background (backlight) and contrast of the camera image",
    unit: "0–255 luminance, contrast", range: "Face 90–190 · contrast ≥ 30 · face ≥ background − 15", source: "lib/lighting.ts" },
  { metric: "Confidence", meaning: "How confident you come across",
    method: "0.40 × speech (pace, pauses, fluency) + 0.35 × face (expression, tension) + 0.25 × body (posture, stability), re-weighted over the parts measured",
    unit: "0–100", range: "≥ 75 High · ≥ 50 Medium · < 50 Low", source: "live/scoring.py" },
  { metric: "Overall score", meaning: "One summary number",
    method: "0.25 fluency + 0.25 pronunciation + 0.20 confidence + 0.15 eye contact + 0.15 posture, re-weighted over the parts measured (listed as “scored on”)",
    unit: "0–100", range: "≥ 85 Excellent · ≥ 70 Good · ≥ 55 Fair", source: "live/scoring.py" },
  { metric: "Gaze tunneling", meaning: "Do you look away when you stumble?",
    method: "Pearson r between gaze aversion and disfluency events per 5 s window, computed in the browser during the session",
    unit: "r (−1…1)", range: "> 0.4 strong link · > 0.15 some link", source: "session page" },
  { metric: "Recommendations", meaning: "What to work on next",
    method: "Each measured issue becomes a candidate with its evidence, a drill and a target relative to your current value, ranked by distance from the comfortable range; the local LLM picks and words the top 3 but may only use measured candidates",
    unit: "—", range: "Max 3 per session", source: "live/coaching.py" },
];

const PRACTICE: Row[] = [
  { metric: "Deck insights", meaning: "What the deck says, before you practise",
    method: "Slide text (python-pptx / pdftotext) → LLM summary, main message, structure, key point per slide, suggestions; measured words per slide (text-heavy > 70 words or > 9 lines)",
    unit: "—", range: "Talk length estimate: 0.75–1.5 min per slide", source: "deck_insights.py" },
  { metric: "Pace vs. example", meaning: "Your pace against the example narration",
    method: "Your words/min vs. the example's words/min for the same slides", unit: "words/min", range: "Within ±15% of the example", source: "coach/metrics.py" },
  { metric: "Duration ratio", meaning: "Too short or too long?",
    method: "Your recording length ÷ the example's length", unit: "ratio", range: "0.75–1.3", source: "coach/metrics.py" },
  { metric: "Key-term coverage", meaning: "Did you say the important words?",
    method: "Share of the example script's top 25 content words that appear in your transcript (light stemming)", unit: "%", range: "≥ 70% good", source: "coach/metrics.py" },
  { metric: "Long pauses", meaning: "Silences that break the flow",
    method: "ffmpeg silence detection; silences ≥ 2 s away from the start/end", unit: "count, timestamps", range: "0–1 per minute", source: "coach/metrics.py" },
  { metric: "OIS feedback", meaning: "Observation → Impact → Suggestion",
    method: "LLM turns the measured numbers into 1–3 items (validated JSON, < 150 words, re-prompted once); rule-based from the same numbers without an LLM",
    unit: "—", range: "—", source: "coach/feedback.py" },
];

const EVALUATION = [
  { component: "Speech recognition", metric: "Word error rate (WER), split by Malay / English / mixed", truth: "FLEURS ms_my (real speakers) + Malaysian-accented and Manglish clips",
    target: "Clear WER reduction vs. a standard Whisper baseline", result: "Done — 7.9% vs 51.3% (docs/benchmarks)" },
  { component: "Pronunciation", metric: "Pearson / Spearman correlation with human ratings; precision/recall of unclear words", truth: "2–3 raters on ~20 clips",
    target: "Correlation ≥ 0.7", result: "Planned" },
  { component: "Stutter & filler detection", metric: "Precision, recall, F1; false-positive rate reported separately", truth: "Manually annotated repetitions, blocks, prolongations, fillers",
    target: "F1 ≥ 0.75, low false positives", result: "Planned" },
  { component: "Eye contact / gaze", metric: "Agreement with a human coding the same video; gaze-tunneling correlation vs. rated naturalness", truth: "Manually coded video",
    target: "Accuracy ≥ 0.8", result: "Planned" },
  { component: "Posture & expression", metric: "Classification accuracy vs. observation", truth: "Manual labels per clip",
    target: "—", result: "Planned" },
  { component: "Overall score", metric: "Correlation with a supervisor's rating", truth: "Supervisor ratings", target: "—", result: "Planned" },
  { component: "Feedback quality", metric: "5-point Likert: specificity, actionability, perceived accuracy (no BLEU/ROUGE — it's coaching text)", truth: "User acceptance testing",
    target: "Significant gain over generic advice", result: "Planned" },
];

function Matrix({ rows }: { rows: Row[] }) {
  return (
    <div className="overflow-x-auto" style={{ border: "1px solid var(--line)" }}>
      <table className="w-full text-sm min-w-[860px]">
        <thead>
          <tr style={{ background: "var(--surface-2)" }}>
            {["Metric", "How it's measured", "Unit", "Range used for feedback", "Source"].map((h) => (
              <th key={h} className="text-left text-[11px] font-semibold uppercase tracking-wide px-3 py-2 text-[var(--muted)]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.metric} className="align-top" style={{ borderTop: "1px solid var(--line)", background: "var(--surface)" }}>
              <td className="px-3 py-2.5 w-[18%]">
                <p className="font-semibold text-[var(--ink)]">{r.metric}</p>
                <p className="text-xs text-[var(--muted)] mt-0.5">{r.meaning}</p>
              </td>
              <td className="px-3 py-2.5 text-[var(--ink-3)] leading-relaxed">{r.method}</td>
              <td className="px-3 py-2.5 text-[var(--ink-2)] whitespace-nowrap">{r.unit}</td>
              <td className="px-3 py-2.5 text-[var(--ink-2)] w-[20%]">{r.range}</td>
              <td className="px-3 py-2.5 font-mono text-[11px] text-[var(--muted)] whitespace-nowrap">{r.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const TABS = [
  { id: "live", label: "Live session metrics" },
  { id: "practice", label: "Presentation practice" },
  { id: "evaluation", label: "Project evaluation" },
] as const;

export default function MethodologyPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("live");

  return (
    <div className="px-4 sm:px-6 py-6 sm:py-8 max-w-[1200px] mx-auto space-y-6">
      <header>
        <h1 className="font-display text-2xl text-[var(--ink)]">Reference matrix</h1>
        <p className="text-sm text-[var(--muted)] mt-1 max-w-[720px]">
          Exactly how every number in SpeechMate is measured, the ranges used to give feedback, and how each part of the
          system is evaluated. Metrics whose model isn&rsquo;t available are shown as unavailable in your results, never estimated.
        </p>
      </header>

      <nav className="flex gap-6 text-sm overflow-x-auto" style={{ borderBottom: "1px solid var(--line)" }} aria-label="Matrix sections">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className="relative py-2.5 whitespace-nowrap"
            style={{ color: tab === t.id ? "var(--ink)" : "var(--muted)", fontWeight: tab === t.id ? 600 : 400 }}>
            {t.label}
            {tab === t.id && <span className="absolute left-0 right-0 -bottom-px h-[2px]" style={{ background: "var(--accent-ink)" }} />}
          </button>
        ))}
      </nav>

      {tab === "live" && <Matrix rows={LIVE} />}
      {tab === "practice" && <Matrix rows={PRACTICE} />}
      {tab === "evaluation" && (
        <div className="overflow-x-auto" style={{ border: "1px solid var(--line)" }}>
          <table className="w-full text-sm min-w-[860px]">
            <thead>
              <tr style={{ background: "var(--surface-2)" }}>
                {["Component", "Evaluation metric", "Ground truth", "Target", "Status"].map((h) => (
                  <th key={h} className="text-left text-[11px] font-semibold uppercase tracking-wide px-3 py-2 text-[var(--muted)]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {EVALUATION.map((r) => (
                <tr key={r.component} className="align-top" style={{ borderTop: "1px solid var(--line)", background: "var(--surface)" }}>
                  <td className="px-3 py-2.5 font-semibold text-[var(--ink)] w-[16%]">{r.component}</td>
                  <td className="px-3 py-2.5 text-[var(--ink-3)]">{r.metric}</td>
                  <td className="px-3 py-2.5 text-[var(--ink-2)]">{r.truth}</td>
                  <td className="px-3 py-2.5 text-[var(--ink-2)]">{r.target}</td>
                  <td className="px-3 py-2.5 whitespace-nowrap" style={{ color: r.result.startsWith("Done") ? "var(--ok)" : "var(--muted)" }}>{r.result}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
