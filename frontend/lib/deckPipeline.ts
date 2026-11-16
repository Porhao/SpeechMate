// Where each deck is in its practice pipeline, from its preparation status and your live
// sessions on it: Preparing → Ready to present → Presented → Q&A rehearsed.
// Used by the Presentations board and the Home task list.

import type { DeckListItem, DeckStatus, LiveSession } from "@/types";
import { overallScore } from "@/lib/scores";

// The deck preparation's statuses (backend/app/models/session.py SESSION_IN_PROGRESS_STATUSES)
export const DECK_IN_PROGRESS: ReadonlySet<DeckStatus> = new Set(["queued", "processing_slides", "analyzing_content"]);
export const DECK_STATUS_LABEL: Record<DeckStatus, string> = {
  queued: "Queued", processing_slides: "Reading slides", analyzing_content: "Understanding them", complete: "Ready", failed: "Failed",
};
// The two preparation steps, as the upload hoop and the deck page show them
export const PREP_STEPS = { reading: "Reading your slides", understanding: "Understanding them: summary, key points, Q&A questions" };
export const SUPPORTED_DECK = /\.(pptx|pdf)$/i;
/** "Week 3 talk.pptx" → "Week 3 talk" */
export const deckTitle = (filename: string) => filename.replace(SUPPORTED_DECK, "");

export type DeckStage = "preparing" | "ready" | "presented" | "rehearsed";

export const STAGES: { id: DeckStage; label: string; hint: string; bg: string; fg: string; onDark: boolean }[] = [
  { id: "preparing", label: "Preparing", hint: "Reading the slides", bg: "var(--surface-3)", fg: "var(--ink)", onDark: false },
  { id: "ready", label: "Ready to present", hint: "Insights done: present it", bg: "var(--peach)", fg: "#0A0A0A", onDark: false },
  { id: "presented", label: "Presented", hint: "Next: rehearse the Q&A", bg: "var(--lavender)", fg: "#0A0A0A", onDark: false },
  { id: "rehearsed", label: "Q&A rehearsed", hint: "Practise again any time", bg: "var(--teal)", fg: "#FFFFFF", onDark: true },
];

export interface DeckProgress {
  deck: DeckListItem;
  stage: DeckStage;
  step: number;          // 1–4: how far along the pipeline
  talks: number;         // sessions presenting it
  rehearsals: number;    // Q&A sessions on it
  best: number | null;   // best overall score across them
  lastAt: string | null; // the latest attempt
}

export function deckProgress(deck: DeckListItem, sessions: LiveSession[]): DeckProgress {
  const mine = sessions.filter((s) => s.context?.deck_id === deck.session_id);
  const talks = mine.filter((s) => s.context?.kind === "talk").length;
  const rehearsals = mine.length - talks;
  const scores = mine.map((s) => overallScore(s.analysis)).filter((v): v is number => v != null);
  const stage: DeckStage = deck.status !== "complete" ? "preparing" : rehearsals ? "rehearsed" : talks ? "presented" : "ready";
  return {
    deck, stage, step: STAGES.findIndex((s) => s.id === stage) + 1, talks, rehearsals,
    best: scores.length ? Math.round(Math.max(...scores)) : null,
    lastAt: mine[0]?.created_at ?? null,  // sessions are newest first
  };
}
