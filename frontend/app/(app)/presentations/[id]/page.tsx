"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft, Loader2, Mic, Square, Upload, Send, AlertTriangle, RotateCcw, X, CheckCircle2, XCircle, MessagesSquare,
} from "lucide-react";
import { presentationService, DECK_IN_PROGRESS, PRACTICE_IN_PROGRESS } from "@/services/presentation";
import { liveService } from "@/services/live";
import { useRecorder } from "@/hooks/useRecorder";
import GenerationProgress from "@/components/presentation/GenerationProgress";
import DeckInsightsPanel from "@/components/presentation/DeckInsightsPanel";
import FeedbackPanel from "@/components/presentation/FeedbackPanel";
import CoachChat from "@/components/presentation/CoachChat";
import type { DeckStatusResponse, PracticeRun, RecordingGranularity, SlideScript } from "@/types";
import { formatDuration } from "@/utils/format";

const POLL_MS = 3000;

const PRACTICE_STAGE: Record<string, string> = {
  queued: "Queued…",
  transcribing: "Transcribing your recording…",
  analyzing: "Analyzing your delivery…",
};

const AUDIO_SOURCE_LABEL: Record<string, string> = {
  elevenlabs_clone: "your cloned voice",
  malaysian_tts: "Malaysian TTS voice",
  kokoro: "Kokoro voice",
  openai_tts: "standard AI voice",
  espeak: "offline synthetic voice",
  silence: "silent (no voice available)",
};

function formatAttemptTime(iso: string) {
  return new Date(iso).toLocaleString("en-MY", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

// The three steps of presentation practice, and the Q&A rehearsal launcher
function PracticeSteps({ deck }: { deck: DeckStatusResponse }) {
  const router = useRouter();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const startQA = async () => {
    setStarting(true); setError(null);
    try {
      const s = await liveService.start({ session_type: "Presentation", deck_id: deck.session_id });
      router.push(`/session?mode=Presentation&live=${s.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't prepare the Q&A");
      setStarting(false);
    }
  };
  const steps = [
    { title: "Understand the deck", body: "Summary, structure, each slide's key point and likely questions.", done: !!deck.insights },
    { title: "Rehearse the talk", body: "Watch the example, record the whole deck or one slide, get coached.", done: false },
    { title: "Rehearse the Q&A", body: "A moderator asks audience questions drawn from your deck; feedback on every answer.", done: false },
  ];
  return (
    <div className="grid md:grid-cols-3" style={{ border: "1px solid var(--line)", background: "var(--surface)" }}>
      {steps.map((st, i) => (
        <div key={st.title} className="p-4" style={{ borderLeft: i ? "1px solid var(--line)" : undefined }}>
          <p className="text-xs font-semibold flex items-center gap-1.5" style={{ color: st.done ? "var(--ok)" : "var(--muted)" }}>
            {st.done ? <CheckCircle2 className="w-3.5 h-3.5" /> : <span className="w-3.5 text-center">{i + 1}</span>} Step {i + 1}
          </p>
          <p className="text-sm font-semibold mt-1" style={{ color: "var(--ink)" }}>{st.title}</p>
          <p className="text-xs mt-0.5 leading-relaxed" style={{ color: "var(--muted)" }}>{st.body}</p>
          {i === 2 && (
            <>
              <button onClick={startQA} disabled={!deck.insights || starting}
                className="mt-3 inline-flex items-center gap-2 h-9 px-3 text-sm font-semibold text-white disabled:opacity-40"
                style={{ background: "var(--accent)" }}>
                {starting ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessagesSquare className="w-4 h-4" />}
                {starting ? "Preparing questions…" : "Start Q&A rehearsal"}
              </button>
              {!deck.insights && <p className="text-xs mt-1.5" style={{ color: "var(--muted)" }}>Available once the deck has been analysed.</p>}
              {error && <p className="text-xs mt-1.5" style={{ color: "var(--bad)" }}>{error}</p>}
            </>
          )}
        </div>
      ))}
    </div>
  );
}

export default function PresentationWorkspace() {
  const { id } = useParams<{ id: string }>();

  const [deck, setDeck] = useState<DeckStatusResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [scripts, setScripts] = useState<SlideScript[]>([]);
  const [runs, setRuns] = useState<PracticeRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  // ── Deck status polling (Stage 2) ─────────────────────────────────────────
  const loadDeck = useCallback(async () => {
    try {
      setDeck(await presentationService.get(id));
      setLoadError(null);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Couldn't load this presentation.");
    }
  }, [id]);

  useEffect(() => {
    presentationService.get(id).then(setDeck).catch((e: Error) => setLoadError(e.message));
  }, [id]);

  useEffect(() => {
    if (!deck || !DECK_IN_PROGRESS.has(deck.status)) return;
    const t = setTimeout(loadDeck, POLL_MS);
    return () => clearTimeout(t);
  }, [deck, loadDeck]);

  const complete = deck?.status === "complete";

  // ── Stage 3 data ──────────────────────────────────────────────────────────
  const loadRuns = useCallback(async () => {
    const list = await presentationService.listPractice(id);
    setRuns(list);
    return list;
  }, [id]);

  useEffect(() => {
    if (!complete) return;
    presentationService.scripts(id).then(setScripts).catch(() => null);
    presentationService.listPractice(id)
      .then((list) => {
        setRuns(list);
        setSelectedRunId((cur) => cur ?? list.at(-1)?.practice_id ?? null);
      })
      .catch(() => null);
  }, [complete, id]);

  // Poll while any practice run is still being analyzed.
  useEffect(() => {
    if (!runs.some((r) => PRACTICE_IN_PROGRESS.has(r.status))) return;
    const t = setTimeout(() => { loadRuns().catch(() => null); }, POLL_MS);
    return () => clearTimeout(t);
  }, [runs, loadRuns]);

  const retry = async () => {
    setRetrying(true);
    try {
      await presentationService.retry(id);
      await loadDeck();
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Retry failed.");
    } finally {
      setRetrying(false);
    }
  };

  if (loadError && !deck) {
    return (
      <div className="px-4 py-10 max-w-[560px] mx-auto text-center space-y-3">
        <p className="text-sm" style={{ color: "var(--bad)" }}>{loadError}</p>
        <Link href="/presentations" className="text-sm underline" style={{ color: "var(--accent-ink)" }}>Back to presentations</Link>
      </div>
    );
  }
  if (!deck) {
    return <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--faint)" }} /></div>;
  }

  return (
    <div className="px-4 sm:px-6 py-6 max-w-[1320px] mx-auto space-y-5">
      <div className="flex items-center gap-3 flex-wrap">
        <Link href="/presentations" className="p-2 rounded-xl" style={{ background: "var(--surface-2)", border: "1px solid var(--line)" }} aria-label="Back">
          <ArrowLeft className="w-4 h-4" style={{ color: "var(--ink-2)" }} />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="font-display text-xl truncate" style={{ color: "var(--ink)" }}>{deck.original_filename}</h1>
          <p className="text-xs" style={{ color: "var(--faint)" }}>
            {deck.slide_count ? `${deck.slide_count} slides` : "Presentation"}
            {complete && deck.voice_cloning_used != null && ` · narrated in ${deck.voice_cloning_used ? "your cloned voice" : deck.narrator_voice ? `the “${deck.narrator_voice}” voice` : "a standard voice"}`}
          </p>
        </div>
        {complete && (
          <button onClick={retry} disabled={retrying} className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-xl disabled:opacity-50"
            style={{ color: "var(--muted)", border: "1px solid var(--line)", background: "var(--surface-2)" }}>
            {retrying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />} Regenerate
          </button>
        )}
      </div>

      {loadError && <p className="text-sm" style={{ color: "var(--bad)" }}>{loadError}</p>}

      <PracticeSteps deck={deck} />

      {!complete ? (
        <>
          <GenerationProgress deck={deck} onRetry={retry} retrying={retrying} />
          {/* Insights are ready right after the slides are parsed — read them while the video builds */}
          {deck.insights && <div className="max-w-[880px] mx-auto"><DeckInsightsPanel insights={deck.insights} /></div>}
        </>
      ) : (
        <>
          {deck.warnings.length > 0 && (
            <div className="text-xs px-4 py-3 rounded-xl space-y-1" style={{ background: "rgba(138,90,34,0.07)", border: "1px solid rgba(138,90,34,0.22)", color: "#6B4419" }}>
              {deck.warnings.map((w, i) => (
                <p key={i} className="flex gap-1.5"><AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-px" />{w}</p>
              ))}
            </div>
          )}
          {deck.insights && <DeckInsightsPanel insights={deck.insights} defaultOpen={false} />}
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] gap-5 items-start">
            <IdealPanel sessionId={id} scripts={scripts} />
            <div className="space-y-5">
              <PracticeRecorder
                sessionId={id}
                scripts={scripts}
                onSubmitted={async (pid) => { await loadRuns().catch(() => null); setSelectedRunId(pid); }}
              />
              <AttemptsPanel sessionId={id} runs={runs} selectedId={selectedRunId} onSelect={setSelectedRunId} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Ideal video + synced script panel ───────────────────────────────────────
function IdealPanel({ sessionId, scripts }: { sessionId: string; scripts: SlideScript[] }) {
  const video = useRef<HTMLVideoElement>(null);
  const [time, setTime] = useState(0);
  const items = useRef<Record<number, HTMLButtonElement | null>>({});

  const current = useMemo(() => {
    const hit = scripts.find((s) => s.start_sec != null && s.duration_sec != null
      && time >= s.start_sec && time < s.start_sec + s.duration_sec);
    return hit?.slide_index ?? null;
  }, [scripts, time]);

  useEffect(() => {
    if (current != null) items.current[current]?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [current]);

  const seek = (s: SlideScript) => {
    if (video.current && s.start_sec != null) {
      video.current.currentTime = s.start_sec;
      video.current.play().catch(() => null);
    }
  };

  return (
    <div className="glass-card rounded-2xl p-4 space-y-4">
      <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>Example presentation</p>
      <video
        ref={video}
        src={presentationService.videoUrl(sessionId)}
        controls
        preload="metadata"
        onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
        className="w-full rounded-xl bg-black aspect-video"
      />
      <div className="max-h-[420px] overflow-y-auto space-y-2 pr-1">
        {scripts.map((s) => {
          const active = s.slide_index === current;
          return (
            <button
              key={s.slide_index}
              ref={(el) => { items.current[s.slide_index] = el; }}
              onClick={() => seek(s)}
              className="w-full text-left rounded-xl p-3 transition-colors"
              style={{
                background: active ? "rgba(35,52,92,0.08)" : "var(--bg)",
                border: `1px solid ${active ? "rgba(35,52,92,0.35)" : "var(--line)"}`,
              }}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[11px] font-bold" style={{ color: active ? "#23345C" : "var(--muted)" }}>Slide {s.slide_index}</span>
                {s.start_sec != null && <span className="text-[11px] tabular-nums" style={{ color: "var(--faint)" }}>{formatDuration(Math.floor(s.start_sec))}</span>}
                {s.script_source === "fallback" && (
                  <span className="text-[10px] px-1.5 rounded" style={{ background: "#8A5A2214", color: "var(--warn)" }}>template script</span>
                )}
              </div>
              <p className="text-sm leading-relaxed" style={{ color: "var(--ink-3)" }}>{s.script_text ?? "—"}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Practice recording / upload ─────────────────────────────────────────────
function PracticeRecorder({ sessionId, scripts, onSubmitted }: {
  sessionId: string; scripts: SlideScript[]; onSubmitted: (practiceId: string) => void | Promise<void>;
}) {
  const rec = useRecorder();
  const [granularity, setGranularity] = useState<RecordingGranularity>("whole_deck");
  const [slide, setSlide] = useState(1);
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const recording = file ?? rec.blob;
  const slideInfo = scripts.find((s) => s.slide_index === slide);

  const submit = async () => {
    if (!recording || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const { practice_id } = await presentationService.submitPractice(
        sessionId, recording, granularity, granularity === "per_slide" ? slide : undefined,
      );
      rec.reset();
      setFile(null);
      await onSubmitted(practice_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="glass-card rounded-2xl p-4 space-y-4">
      <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>Your practice</p>

      <div className="flex gap-2">
        {(["whole_deck", "per_slide"] as const).map((g) => (
          <button key={g} onClick={() => setGranularity(g)} className="text-xs font-medium px-3 py-1.5 rounded-lg"
            style={granularity === g
              ? { background: "var(--accent)", color: "white" }
              : { background: "var(--surface-2)", color: "var(--ink-2)", border: "1px solid var(--line)" }}>
            {g === "whole_deck" ? "Whole deck" : "One slide"}
          </button>
        ))}
      </div>

      {granularity === "per_slide" && scripts.length > 0 && (
        <div className="space-y-3">
          <select value={slide} onChange={(e) => setSlide(Number(e.target.value))}
            className="text-sm px-3 py-2 rounded-lg outline-none"
            style={{ background: "var(--surface-2)", border: "1px solid var(--line)", color: "var(--ink)" }}>
            {scripts.map((s) => <option key={s.slide_index} value={s.slide_index}>Slide {s.slide_index}</option>)}
          </select>
          {/* eslint-disable-next-line @next/next/no-img-element -- served by the backend, not a static asset */}
          <img src={presentationService.slideImageUrl(sessionId, slide)} alt={`Slide ${slide}`}
            className="w-full rounded-lg" style={{ border: "1px solid var(--line)" }} />
          {slideInfo?.audio_source && slideInfo.audio_source !== "silence" && (
            <div>
              <p className="text-[11px] mb-1" style={{ color: "var(--faint)" }}>
                Ideal narration ({AUDIO_SOURCE_LABEL[slideInfo.audio_source] ?? slideInfo.audio_source})
              </p>
              <audio key={slide} src={presentationService.slideAudioUrl(sessionId, slide)} controls className="w-full h-9" />
            </div>
          )}
        </div>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        {!rec.recording ? (
          <button onClick={() => { setFile(null); rec.start(); }} disabled={submitting}
            className="flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-xl text-white disabled:opacity-50" style={{ background: "#8C3B32" }}>
            <Mic className="w-4 h-4" /> {rec.blob ? "Re-record" : "Record"}
          </button>
        ) : (
          <button onClick={rec.stop} className="flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-xl text-white" style={{ background: "#17181C" }}>
            <Square className="w-4 h-4" /> Stop · {formatDuration(rec.seconds)}
          </button>
        )}
        <input ref={fileInput} type="file" accept="audio/*,video/*,.m4a,.webm,.ogg,.flac,.mov" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) { rec.reset(); setFile(f); } e.target.value = ""; }} />
        <button onClick={() => fileInput.current?.click()} disabled={rec.recording || submitting}
          className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-xl disabled:opacity-50"
          style={{ background: "var(--surface-2)", border: "1px solid var(--line)", color: "var(--ink)" }}>
          <Upload className="w-4 h-4" /> Upload file
        </button>
      </div>
      {rec.error && <p className="text-xs" style={{ color: "var(--bad)" }}>{rec.error}</p>}

      {recording && !rec.recording && (
        <div className="rounded-xl p-3 space-y-2" style={{ background: "var(--surface-2)", border: "1px solid var(--line)" }}>
          {file ? (
            <p className="flex items-center gap-2 text-sm" style={{ color: "var(--ink)" }}>
              {file.name}
              <button onClick={() => setFile(null)} aria-label="Remove file"><X className="w-3.5 h-3.5" /></button>
            </p>
          ) : rec.url && <audio src={rec.url} controls className="w-full h-9" />}
          <button onClick={submit} disabled={submitting}
            className="flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-xl text-white disabled:opacity-50" style={{ background: "var(--accent)" }}>
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Get feedback{granularity === "per_slide" ? ` on slide ${slide}` : ""}
          </button>
        </div>
      )}
      {error && <p className="text-sm" style={{ color: "var(--bad)" }}>{error}</p>}
    </div>
  );
}

// ── Attempts history + selected feedback + chat ─────────────────────────────
function AttemptsPanel({ sessionId, runs, selectedId, onSelect }: {
  sessionId: string; runs: PracticeRun[]; selectedId: string | null; onSelect: (id: string) => void;
}) {
  if (runs.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-4">
        <p className="text-sm" style={{ color: "var(--faint)" }}>
          Watch the example, then record yourself presenting. Your coach feedback will appear here.
        </p>
      </div>
    );
  }
  const selected = runs.find((r) => r.practice_id === selectedId) ?? runs.at(-1)!;
  const newestFirst = [...runs].reverse();

  return (
    <div className="glass-card rounded-2xl p-4 space-y-4">
      <div>
        <p className="text-sm font-semibold mb-2" style={{ color: "var(--ink)" }}>Attempts</p>
        <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
          {newestFirst.map((r) => {
            const n = runs.indexOf(r) + 1;
            const active = r.practice_id === selected.practice_id;
            return (
              <button key={r.practice_id} onClick={() => onSelect(r.practice_id)}
                className="flex-shrink-0 text-left text-xs px-3 py-2 rounded-xl"
                style={active
                  ? { background: "var(--accent)", color: "white" }
                  : { background: "var(--surface-2)", color: "var(--ink-2)", border: "1px solid var(--line)" }}>
                <span className="flex items-center gap-1 font-semibold">
                  #{n} {r.recording_granularity === "per_slide" ? `· slide ${r.slide_index}` : "· whole deck"}
                  {r.status === "complete" && <CheckCircle2 className="w-3 h-3" />}
                  {r.status === "failed" && <XCircle className="w-3 h-3" />}
                  {PRACTICE_IN_PROGRESS.has(r.status) && <Loader2 className="w-3 h-3 animate-spin" />}
                </span>
                <span className="opacity-70">{formatAttemptTime(r.created_at)}</span>
              </button>
            );
          })}
        </div>
      </div>

      {PRACTICE_IN_PROGRESS.has(selected.status) && (
        <div className="flex items-center gap-2 text-sm py-4" style={{ color: "var(--accent-ink)" }}>
          <Loader2 className="w-4 h-4 animate-spin" /> {PRACTICE_STAGE[selected.status]}
        </div>
      )}

      {selected.status === "failed" && (
        <p className="text-sm px-3 py-2 rounded-lg" style={{ background: "rgba(140,59,50,0.06)", color: "var(--bad)", border: "1px solid rgba(140,59,50,0.2)" }}>
          {selected.error_detail ?? "Analysis failed."} Record or upload again to retry.
        </p>
      )}

      {selected.status === "complete" && (
        <>
          <FeedbackPanel run={selected} />
          <div className="pt-4" style={{ borderTop: "1px solid var(--line-2)" }}>
            <p className="text-sm font-semibold mb-3" style={{ color: "var(--ink)" }}>Ask your coach</p>
            <CoachChat key={selected.practice_id} sessionId={sessionId} practiceId={selected.practice_id} compact />
          </div>
        </>
      )}
    </div>
  );
}
