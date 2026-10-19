// Where each deck is in its practice pipeline, from its preparation status and your live
// sessions on it: Preparing → Ready to present → Presented → Q&A rehearsed.
// Used by the Presentations board and the Home task list.

import type { DeckListItem, LiveSession } from "@/types";

export type DeckStage = "preparing" | "ready" | "presented" | "rehearsed";

export const STAGES: { id: DeckStage; label: string; hint: string; bg: string; fg: string }[] = [
  { id: "preparing", label: "Preparing", hint: "Reading the slides", bg: "var(--surface-3)", fg: "var(--ink)" },
  { id: "ready", label: "Ready to present", hint: "Insights done: present it", bg: "var(--peach)", fg: "#0A0A0A" },
  { id: "presented", label: "Presented", hint: "Next: rehearse the Q&A", bg: "var(--lavender)", fg: "#0A0A0A" },
  { id: "rehearsed", label: "Q&A rehearsed", hint: "Practise again any time", bg: "var(--teal)", fg: "#FFFFFF" },
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
  const scores = mine.map((s) => s.analysis?.communication_score.overall_score).filter((v): v is number => v != null);
  const stage: DeckStage = deck.status !== "complete" ? "preparing" : rehearsals ? "rehearsed" : talks ? "presented" : "ready";
  return {
    deck, stage, step: STAGES.findIndex((s) => s.id === stage) + 1, talks, rehearsals,
    best: scores.length ? Math.round(Math.max(...scores)) : null,
    lastAt: mine[0]?.created_at ?? null,  // sessions are newest first
  };
}
