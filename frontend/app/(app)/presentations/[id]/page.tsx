"use client";

// One deck: what the AI understood from it, then the two ways to practise it.
//   1. Present it: your slides on screen, you move through them; what you say on each slide is
//      checked against what the slide is about (plus voice, body language and confidence).
//   2. Rehearse the Q&A: audience questions drawn from the deck, with feedback on each answer.
// Past attempts on this deck are listed with their scores.

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { AlertTriangle, ArrowLeft, ChevronRight, Loader2, MessagesSquare, Presentation, RotateCcw } from "lucide-react";
import { presentationService, DECK_IN_PROGRESS } from "@/services/presentation";
import { authService } from "@/services/auth";
import { liveService } from "@/services/live";
import GenerationProgress from "@/components/presentation/GenerationProgress";
import DeckInsightsPanel from "@/components/presentation/DeckInsightsPanel";
import { Card, Notice, statusColor } from "@/components/ui/kit";
import type { DeckStatusResponse, LiveSession } from "@/types";
import { formatDuration } from "@/utils/format";

const POLL_MS = 3000;

export default function PresentationWorkspace() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [deck, setDeck] = useState<DeckStatusResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [starting, setStarting] = useState<"talk" | "qa" | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [attempts, setAttempts] = useState<LiveSession[] | null>(null);

  const loadDeck = useCallback(async () => {
    try { setDeck(await presentationService.get(id)); setLoadError(null); }
    catch (e) { setLoadError(e instanceof Error ? e.message : "Couldn't load this presentation."); }
  }, [id]);

  useEffect(() => {
    presentationService.get(id).then(setDeck).catch((e: Error) => setLoadError(e.message));
    if (authService.isSignedIn()) {
      liveService.history().then((l) => setAttempts(l.filter((s) => s.context?.deck_id === id))).catch(() => setAttempts([]));
    }
  }, [id]);

  useEffect(() => {
    if (!deck || !DECK_IN_PROGRESS.has(deck.status)) return;
    const t = setTimeout(loadDeck, POLL_MS);
    return () => clearTimeout(t);
  }, [deck, loadDeck]);

  const ready = deck?.status === "complete" || !!deck?.insights;
  const keyPoints = useMemo(() => new Map((deck?.insights?.slides ?? []).map((s) => [s.slide_index, s.key_point])), [deck]);

  const start = async (mode: "talk" | "qa") => {
    if (!authService.isSignedIn()) { router.push(`/login?next=/presentations/${id}`); return; }
    setStarting(mode); setStartError(null);
    try {
      const s = await liveService.start({ session_type: "Presentation", deck_id: id, presentation_mode: mode });
      router.push(`/session?mode=Presentation&live=${s.id}`);
    } catch (e) {
      setStartError(e instanceof Error ? e.message : "Couldn't start the session");
      setStarting(null);
    }
  };

  const retry = async () => {
    setRetrying(true);
    try { await presentationService.retry(id); await loadDeck(); }
    catch (e) { setLoadError(e instanceof Error ? e.message : "Retry failed."); }
    finally { setRetrying(false); }
  };

  if (loadError && !deck) {
    return (
      <div className="px-4 py-10 max-w-[560px] mx-auto text-center space-y-3">
        <p className="text-sm" style={{ color: "var(--bad)" }}>{loadError}</p>
        <Link href="/presentations" className="text-sm underline" style={{ color: "var(--accent-ink)" }}>Back to presentations</Link>
      </div>
    );
  }
  if (!deck) return <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--faint)" }} /></div>;

  const slides = Array.from({ length: deck.slide_count ?? 0 }, (_, i) => i + 1);

  return (
    <div className="px-4 sm:px-6 py-8 max-w-[1200px] mx-auto space-y-6">
      <div className="flex items-center gap-3 flex-wrap">
        <Link href="/presentations" className="nav-pill w-10 h-10 rounded-full flex items-center justify-center" aria-label="Back to presentations">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="font-display text-3xl truncate" style={{ color: "var(--ink)" }}>{deck.original_filename.replace(/\.(pptx|pdf)$/i, "")}</h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            {deck.slide_count ? `${deck.slide_count} slides` : "Presentation"}
            {deck.insights?.stats && ` · aim for about ${deck.insights.stats.estimated_minutes[0]}–${deck.insights.stats.estimated_minutes[1]} min`}
          </p>
        </div>
        {deck.status === "complete" && (
          <button onClick={retry} disabled={retrying} className="nav-pill flex items-center gap-1.5 text-xs px-3 py-2 rounded-full disabled:opacity-50">
            {retrying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />} Re-read the deck
          </button>
        )}
      </div>

      {loadError && <Notice tone="bad">{loadError}</Notice>}
      {!ready && <GenerationProgress deck={deck} onRetry={retry} retrying={retrying} />}

      {ready && (
        <>
          {/* The two ways to practise */}
          <div className="grid md:grid-cols-2 gap-5">
            <div className="clay rounded-xl p-6 flex flex-col" style={{ background: "var(--lavender)", color: "#0A0A0A" }}>
              <Presentation className="w-7 h-7" strokeWidth={1.8} />
              <p className="text-xs font-semibold uppercase tracking-[0.12em] mt-4 opacity-70">Step 2</p>
              <h2 className="font-display text-2xl">Present it</h2>
              <p className="text-sm mt-1.5 leading-relaxed opacity-85 flex-1">
                Your slides fill the screen and you move through them (← → keys or the buttons), talking as you would to a
                real audience. Afterwards: did what you said on each slide match what the slide is about, how long you spent
                on each, plus your voice, body language and confidence.
              </p>
              <button onClick={() => start("talk")} disabled={!!starting}
                className="mt-5 h-12 rounded-md text-base font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-60"
                style={{ background: "#0A0A0A" }}>
                {starting === "talk" ? <Loader2 className="w-5 h-5 animate-spin" /> : <Presentation className="w-5 h-5" />} Present it
              </button>
            </div>
            <div className="clay rounded-xl p-6 flex flex-col" style={{ background: "var(--teal)", color: "#fff" }}>
              <MessagesSquare className="w-7 h-7" strokeWidth={1.8} />
              <p className="text-xs font-semibold uppercase tracking-[0.12em] mt-4 opacity-70">Step 3</p>
              <h2 className="font-display text-2xl">Rehearse the Q&amp;A</h2>
              <p className="text-sm mt-1.5 leading-relaxed opacity-85 flex-1">
                A moderator asks the questions this audience is likely to ask about your deck, one at a time. You get
                feedback on every answer, with a stronger version using only your own facts.
              </p>
              <button onClick={() => start("qa")} disabled={!!starting}
                className="mt-5 h-12 rounded-md text-base font-semibold flex items-center justify-center gap-2 disabled:opacity-60"
                style={{ background: "#fff", color: "#0A0A0A" }}>
                {starting === "qa" ? <Loader2 className="w-5 h-5 animate-spin" /> : <MessagesSquare className="w-5 h-5" />} Start Q&amp;A
              </button>
            </div>
          </div>
          {startError && <Notice tone="bad">{startError}</Notice>}

          {deck.warnings.length > 0 && (
            <Notice tone="warn">
              {deck.warnings.map((w, i) => <span key={i} className="flex gap-1.5"><AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />{w}</span>)}
            </Notice>
          )}

          {/* What each slide must land: what the talk is checked against */}
          {slides.length > 0 && (
            <Card title="Step 1 · What each slide should say">
              <p className="text-sm -mt-2 mb-4" style={{ color: "var(--muted)" }}>
                When you present, what you say on each slide is compared with its content and this key point.
              </p>
              <ol className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {slides.map((n) => (
                  <li key={n} className="rounded-lg overflow-hidden" style={{ border: "1px solid var(--line)" }}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={presentationService.slideImageUrl(id, n)} alt={`Slide ${n}`} loading="lazy"
                      className="w-full aspect-video object-contain" style={{ background: "var(--surface-2)" }} />
                    <p className="px-3 py-2.5 text-sm leading-snug" style={{ color: "var(--ink-2)" }}>
                      <b style={{ color: "var(--ink)" }}>{n}.</b> {keyPoints.get(n) ?? "—"}
                    </p>
                  </li>
                ))}
              </ol>
            </Card>
          )}

          {deck.insights && <DeckInsightsPanel insights={deck.insights} defaultOpen={false} />}

          {/* Past attempts on this deck */}
          {attempts && attempts.length > 0 && (
            <Card title="Your attempts on this deck">
              <ul className="divide-y divide-[var(--line-2)]">
                {attempts.map((s) => {
                  const score = s.analysis?.communication_score.overall_score;
                  const talk = s.context?.kind === "talk";
                  return (
                    <li key={s.id}>
                      <Link href={`/results/${s.id}`} className="flex items-center gap-4 py-3 group">
                        <span className="w-10 text-center font-display text-xl tabular-nums"
                          style={{ color: score != null ? statusColor(score >= 75 ? "good" : score >= 55 ? "ok" : "work") : "var(--faint)" }}>
                          {score != null ? Math.round(score) : "—"}
                        </span>
                        <span className="flex-1 min-w-0">
                          <span className="block text-sm font-medium" style={{ color: "var(--ink)" }}>{talk ? "Presented the deck" : "Q&A rehearsal"}</span>
                          <span className="block text-xs" style={{ color: "var(--muted)" }}>
                            {new Date(s.created_at).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" })} · {formatDuration(s.duration_sec)}
                            {s.status !== "complete" && ` · ${s.status === "analyzing" ? "analysing…" : s.status === "failed" ? "analysis failed" : "not finished"}`}
                          </span>
                        </span>
                        <ChevronRight className="w-4 h-4 opacity-40 group-hover:opacity-100" />
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
