"use client";

import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Mic,
  Volume2,
  Activity,
  Eye,
  Brain,
  Lightbulb,
  ListChecks,
} from "lucide-react";

type MetricCategory = {
  id: string;
  title: string;
  icon: React.ElementType;
  color: string;
  rationale: string;
  metrics: string[];
};

const CATEGORIES: MetricCategory[] = [
  {
    id: "asr",
    title: "Speech Recognition (ASR)",
    icon: Mic,
    color: "#23345C",
    rationale:
      "Standard, comparable across papers, and directly shows Malaysian-accent handling — the project's key differentiator. Implemented as a router, not a single model: faster-whisper handles the English path, and its own language confidence is what decides whether a clip gets re-run through a Malay/code-switching-specific engine instead.",
    metrics: [
      "Word Error Rate (WER) on a local Malaysian-accented test set",
      "WER reported separately for English-only vs. code-switched clips — this split is the novelty claim, and the pipeline keeps both engines' transcripts so the comparison doesn't need a second pass later",
      "Compared against a raw Whisper baseline (no local tuning) — for every clip routed to the code-switching engine, Whisper's own transcript is kept alongside it as that baseline",
      "Code-switching path: mesolitica/wav2vec2-xls-r-300m-mixed (Malay + Singlish + Mandarin-mixed, WER 0.132 / CER 0.048 per its model card) via transformers — the same checkpoint the malaya-speech toolkit itself wraps, loaded directly since it ships native PyTorch weights",
    ],
  },
  {
    id: "pronunciation",
    title: "Pronunciation Assessment",
    icon: Volume2,
    color: "#5A5470",
    rationale:
      "Flagged weak spot — reviewers/examiners will push hardest here, so this uses a correlation metric rather than raw accuracy.",
    metrics: [
      "Pearson or Spearman correlation between the GOP score and a human rater's score (2–3 raters on ~20 clips is enough for an FYP)",
      "Precision/Recall on mispronounced-phoneme detection against manually annotated clips",
      "Per-phoneme-category breakdown (vowels vs. consonants vs. plosives) — plosives/fricatives are where alignment error hits hardest per the literature review",
    ],
  },
  {
    id: "disfluency",
    title: "Disfluency / Stutter Detection",
    icon: Activity,
    color: "#8A5A22",
    rationale: "Matches what was already committed to in the interim report — kept consistent.",
    metrics: [
      "Precision, Recall, F1-score against manually annotated repetitions/prolonged pauses",
      "False-positive rate reported separately — over-flagging normal pauses as stutters undermines the design thesis for anxious users",
    ],
  },
  {
    id: "gaze",
    title: "Gaze / Eye Contact (Gaze Tunneling)",
    icon: Eye,
    color: "#3F6B4C",
    rationale: "The genuinely novel contribution — worth the most rigorous treatment.",
    metrics: [
      "Detection accuracy against manually coded video ground truth (did the AI agree with a human watching the same clip?)",
      "Correlation between the fused gaze-stutter timeline and an independently-rated 'naturalness of eye contact' score from a small panel",
    ],
  },
  {
    id: "feedback",
    title: "AI Feedback Quality",
    icon: Brain,
    color: "#8C3B32",
    rationale:
      "The part actively being improved. Do NOT use BLEU/ROUGE — wrong tool for coaching text, not translation. Human-rated rubrics instead.",
    metrics: [
      "5-point Likert ratings from UAT on: specificity, actionability, and perceived accuracy",
      "Before/after comparison once the prompt structure is improved — a concrete 'we improved X by Y' result for the paper",
    ],
  },
];

export default function MethodologyPage() {
  const router = useRouter();

  return (
    <div className="px-4 sm:px-6 py-6 sm:py-8 max-w-[900px] mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push("/reports")}
          className="w-9 h-9 flex items-center justify-center rounded-xl transition-colors"
          style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#4B4C52" }}
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="font-display text-xl" style={{ color: "#17181C" }}>Evaluation Methodology</h1>
          <p className="text-xs" style={{ color: "#9B988E" }}>
            Reference: the metrics used to evaluate each component of the FYP
          </p>
        </div>
      </div>

      {/* Intro note */}
      <div
        className="rounded-2xl p-5 flex items-start gap-3"
        style={{ background: "rgba(35,52,92,0.06)", border: "1px solid rgba(35,52,92,0.16)" }}
      >
        <Lightbulb className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "#23345C" }} />
        <p className="text-sm leading-relaxed" style={{ color: "#34343A" }}>
          Each component below is evaluated with a metric chosen for what it needs to prove, not
          just what's easiest to compute — e.g. correlation over raw accuracy for pronunciation
          (since ground truth is inherently subjective), and human-rated rubrics over BLEU/ROUGE
          for AI feedback (since it's coaching text, not translation).
        </p>
      </div>

      {/* Categories */}
      <div className="space-y-4">
        {CATEGORIES.map((cat) => (
          <div key={cat.id} className="glass-card rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-3">
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: `${cat.color}14`, border: `1px solid ${cat.color}30` }}
              >
                <cat.icon className="w-4.5 h-4.5" style={{ color: cat.color }} />
              </div>
              <h2 className="text-base font-semibold" style={{ color: "#17181C" }}>{cat.title}</h2>
            </div>

            <p className="text-sm leading-relaxed mb-4" style={{ color: "#6E6C63" }}>{cat.rationale}</p>

            <div className="space-y-2.5">
              {cat.metrics.map((m, i) => (
                <div key={i} className="flex items-start gap-2.5">
                  <ListChecks className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: cat.color }} />
                  <p className="text-sm leading-relaxed" style={{ color: "#34343A" }}>{m}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}
