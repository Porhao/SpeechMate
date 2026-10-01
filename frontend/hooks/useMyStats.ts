"use client";

// Real practice stats from the signed-in user's live sessions (GET /api/live).
// null while loading or when signed out — callers show "—", never made-up numbers.

import { useEffect, useState } from "react";
import { liveService } from "@/services/live";
import { authService } from "@/services/auth";
import type { LiveSession } from "@/types";

export interface MyStats {
  sessions: number;
  practiceMinutes: number;
  latestScore: number | null;
  streakDays: number;
  thisWeek: number;
  byMode: Record<string, { sessions: number; avgScore: number | null }>;
  recent: LiveSession[];
}

const dayKey = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;

function compute(list: LiveSession[]): MyStats {
  const scoreOf = (s: LiveSession) => s.analysis?.communication_score.overall_score ?? null;
  const byMode: MyStats["byMode"] = {};
  for (const s of list) {
    const m = (byMode[s.session_type] ??= { sessions: 0, avgScore: null });
    m.sessions++;
  }
  for (const mode of Object.keys(byMode)) {
    const scores = list.filter((s) => s.session_type === mode).map(scoreOf).filter((v): v is number => v != null);
    byMode[mode].avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null;
  }

  // Consecutive days with a session, ending today (or yesterday, if not practised yet today)
  const days = new Set(list.map((s) => dayKey(new Date(s.created_at))));
  const cursor = new Date();
  if (!days.has(dayKey(cursor))) cursor.setDate(cursor.getDate() - 1);
  let streak = 0;
  while (days.has(dayKey(cursor))) { streak++; cursor.setDate(cursor.getDate() - 1); }

  const weekAgo = Date.now() - 7 * 86_400_000;
  const scored = list.find((s) => scoreOf(s) != null);  // list is newest first
  return {
    sessions: list.length,
    practiceMinutes: Math.round(list.reduce((a, s) => a + s.duration_sec, 0) / 60),
    latestScore: scored ? Math.round(scoreOf(scored)!) : null,
    streakDays: streak,
    thisWeek: list.filter((s) => new Date(s.created_at).getTime() >= weekAgo).length,
    byMode,
    recent: list.slice(0, 5),
  };
}

export function useMyStats(): { stats: MyStats | null; signedIn: boolean } {
  const [stats, setStats] = useState<MyStats | null>(null);
  const [signedIn, setSignedIn] = useState(true);

  useEffect(() => {
    if (!authService.isSignedIn()) {
      const t = setTimeout(() => setSignedIn(false), 0);
      return () => clearTimeout(t);
    }
    let cancelled = false;
    liveService.history()
      .then((list) => { if (!cancelled) setStats(compute(list)); })
      .catch(() => { if (!cancelled) setSignedIn(false); });
    return () => { cancelled = true; };
  }, []);

  return { stats, signedIn };
}
