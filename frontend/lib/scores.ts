// How every 0–100 score is banded and which number heads a session. The bands are the backend's
// (backend/app/services/live/rules.py STRONG / OKAY); the API also sends a status with each score.

import type { FullAnalysisResult, MetricStatus } from "@/types";

export const STRONG = 75, OKAY = 55;

export const statusOf = (v: number | null | undefined): MetricStatus =>
  v == null ? null : v >= STRONG ? "good" : v >= OKAY ? "ok" : "work";

/** A session's headline score: the weighted overall, else (when it couldn't be computed) the mean of its pillars. */
export function overallScore(a: Pick<FullAnalysisResult, "communication_score" | "pillars"> | null | undefined): number | null {
  if (!a) return null;
  if (a.communication_score.overall_score != null) return Math.round(a.communication_score.overall_score);
  const vals = Object.values(a.pillars ?? {}).map((p) => p.score).filter((v): v is number => v != null);
  return vals.length ? Math.round(vals.reduce((x, y) => x + y, 0) / vals.length) : null;
}
