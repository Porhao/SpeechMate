"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Bot, Loader2, Presentation, ChevronRight } from "lucide-react";
import { presentationService } from "@/services/presentation";
import CoachChat from "@/components/presentation/CoachChat";
import GeneralCoachChat from "@/components/coach/GeneralCoachChat";
import FeedbackPanel from "@/components/presentation/FeedbackPanel";
import type { DeckListItem, PracticeRun } from "@/types";
import { cn } from "@/lib/utils";

interface Attempt {
  deck: DeckListItem;
  run: PracticeRun;
  number: number;
}

function formatWhen(iso: string) {
  return new Date(iso).toLocaleString("en-MY", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

// Two coaches: the general AI coach, and the presentation Coach Agent, whose
// chat is grounded in one practice attempt (its metrics, OIS feedback,
// transcript and earlier attempts on the same deck).
const GENERAL = "general";
export default function CoachPage() {
  const [attempts, setAttempts] = useState<Attempt[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string>(GENERAL);

  useEffect(() => {
    (async () => {
      try {
        const decks = (await presentationService.list()).filter((d) => d.status === "complete");
        const perDeck = await Promise.all(decks.map(async (deck) => {
          const runs = await presentationService.listPractice(deck.session_id);
          return runs.map((run, i) => ({ deck, run, number: i + 1 }));
        }));
        const all = perDeck.flat()
          .filter((a) => a.run.status === "complete")
          .sort((a, b) => b.run.created_at.localeCompare(a.run.created_at));
        setAttempts(all);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Couldn't load your practice attempts.");
      }
    })();
  }, []);

  const current = useMemo(
    () => attempts?.find((a) => a.run.practice_id === selected) ?? null,
    [attempts, selected],
  );

  return (
    <div className="px-3 sm:px-6 py-4 sm:py-6 max-w-[1320px] mx-auto">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: "var(--accent)" }}>
          <Bot className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="font-display text-xl" style={{ color: "var(--ink)" }}>AI Coach</h1>
          <p className="text-xs" style={{ color: "var(--muted)" }}>Ask for general coaching, or follow up on a presentation practice attempt.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-5 items-start">
        <div className="glass-card rounded-2xl p-3 space-y-1 lg:max-h-[calc(100dvh-220px)] overflow-y-auto">
          <button
            onClick={() => setSelected(GENERAL)}
            className={cn("w-full text-left px-3 py-2 rounded-xl transition-colors", selected !== GENERAL && "hover:bg-[var(--surface-2)]")}
            style={selected === GENERAL ? { background: "rgba(35,52,92,0.08)", border: "1px solid rgba(35,52,92,0.25)" } : { border: "1px solid transparent" }}
          >
            <p className="text-sm font-medium" style={{ color: "var(--ink)" }}>General coaching</p>
            <p className="text-xs" style={{ color: "var(--faint)" }}>Fluency, pronunciation, confidence, eye contact</p>
          </button>

          <p className="text-[10px] font-semibold uppercase tracking-wide px-3 pt-3 pb-1" style={{ color: "var(--faint)" }}>
            Presentation attempts
          </p>
          {error && <p className="text-xs px-3" style={{ color: "var(--bad)" }}>{error}</p>}
          {attempts === null && !error && <Loader2 className="w-4 h-4 animate-spin mx-3" style={{ color: "var(--faint)" }} />}
          {attempts?.length === 0 && (
            <Link href="/presentations" className="flex items-center gap-2 text-xs px-3 py-2" style={{ color: "var(--warn)" }}>
              <Presentation className="w-4 h-4" /> Practise a deck to chat about it <ChevronRight className="w-3 h-3" />
            </Link>
          )}
          {attempts?.map((a) => (
            <button
              key={a.run.practice_id}
              onClick={() => setSelected(a.run.practice_id)}
              className={cn("w-full text-left px-3 py-2 rounded-xl transition-colors", a.run.practice_id !== selected && "hover:bg-[var(--surface-2)]")}
              style={a.run.practice_id === selected ? { background: "rgba(35,52,92,0.08)", border: "1px solid rgba(35,52,92,0.25)" } : { border: "1px solid transparent" }}
            >
              <p className="text-sm font-medium truncate" style={{ color: "var(--ink)" }}>{a.deck.original_filename}</p>
              <p className="text-xs" style={{ color: "var(--faint)" }}>
                Attempt #{a.number} · {a.run.recording_granularity === "per_slide" ? `slide ${a.run.slide_index}` : "whole deck"} · {formatWhen(a.run.created_at)}
              </p>
            </button>
          ))}
        </div>

        {selected === GENERAL ? (
          <div className="glass-card rounded-2xl p-4 flex flex-col" style={{ height: "min(640px, calc(100dvh - 220px))" }}>
            <p className="text-sm font-semibold mb-3" style={{ color: "var(--ink)" }}>General coaching</p>
            <GeneralCoachChat />
          </div>
        ) : current && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 items-start">
            <div className="glass-card rounded-2xl p-4 flex flex-col" style={{ height: "min(640px, calc(100dvh - 220px))" }}>
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>Chat</p>
                <Link href={`/presentations/${current.deck.session_id}`} className="text-xs underline" style={{ color: "var(--accent-ink)" }}>
                  Open presentation
                </Link>
              </div>
              <CoachChat key={current.run.practice_id} sessionId={current.deck.session_id} practiceId={current.run.practice_id} />
            </div>
            <div className="glass-card rounded-2xl p-4">
              <p className="text-sm font-semibold mb-3" style={{ color: "var(--ink)" }}>Feedback for this attempt</p>
              <FeedbackPanel run={current.run} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
