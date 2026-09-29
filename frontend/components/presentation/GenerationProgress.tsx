"use client";

import { CheckCircle2, Circle, Loader2, XCircle, RotateCcw } from "lucide-react";
import type { DeckStatusResponse } from "@/types";

// Named steps map 1:1 to the Ideal Presentation Agent's status values.
const STEPS = [
  { status: "processing_slides", label: "Parsing slide content", progress: "rendered" },
  { status: "generating_scripts", label: "Generating narration scripts", progress: "scripted" },
  { status: "synthesizing_audio", label: "Synthesizing audio track", progress: "synthesized" },
  { status: "assembling_video", label: "Assembling video", progress: null },
] as const;

export default function GenerationProgress({
  deck, onRetry, retrying,
}: { deck: DeckStatusResponse; onRetry: () => void; retrying: boolean }) {
  const failed = deck.status === "failed";
  const activeIdx = STEPS.findIndex((s) => s.status === deck.status);
  // Where a failed run stopped: the first step whose per-slide count isn't full.
  const p = deck.slides_progress;
  const failedIdx = failed
    ? (!p ? 0 : p.rendered < p.total ? 0 : p.scripted < p.total ? 1 : p.synthesized < p.total ? 2 : 3)
    : -1;

  return (
    <div className="glass-card rounded-2xl p-6 max-w-[560px] mx-auto">
      <h2 className="text-base font-semibold mb-1" style={{ color: "#17181C" }}>
        {failed ? "Generation failed" : deck.status === "queued" ? "Waiting in the queue…" : "Building your example presentation"}
      </h2>
      <p className="text-xs mb-5" style={{ color: "#9B988E" }}>
        {deck.original_filename}{deck.slide_count ? ` · ${deck.slide_count} slides` : ""}
      </p>

      <ol className="space-y-4">
        {STEPS.map((step, i) => {
          const done = failed ? i < failedIdx : activeIdx > i;
          const active = !failed && activeIdx === i;
          const broke = failed && i === failedIdx;
          const count = step.progress && p ? p[step.progress] : null;
          return (
            <li key={step.status} className="flex items-center gap-3">
              {done ? <CheckCircle2 className="w-5 h-5" style={{ color: "#3F6B4C" }} />
                : active ? <Loader2 className="w-5 h-5 animate-spin" style={{ color: "#23345C" }} />
                : broke ? <XCircle className="w-5 h-5" style={{ color: "#8C3B32" }} />
                : <Circle className="w-5 h-5" style={{ color: "#D8D3C6" }} />}
              <span className="text-sm flex-1" style={{ color: done || active || broke ? "#17181C" : "#9B988E", fontWeight: active ? 600 : 400 }}>
                {step.label}
              </span>
              {count != null && p && (active || done) && (
                <span className="text-xs tabular-nums" style={{ color: "#6E6C63" }}>{count}/{p.total}</span>
              )}
            </li>
          );
        })}
      </ol>

      {failed && (
        <div className="mt-5 space-y-3">
          <p className="text-sm px-3 py-2 rounded-lg" style={{ background: "rgba(140,59,50,0.06)", color: "#8C3B32", border: "1px solid rgba(140,59,50,0.2)" }}>
            {deck.error_detail ?? "Something went wrong."}
          </p>
          <button
            onClick={onRetry}
            disabled={retrying}
            className="flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-xl text-white disabled:opacity-50"
            style={{ background: "#23345C" }}
          >
            {retrying ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />} Retry
          </button>
        </div>
      )}
    </div>
  );
}
