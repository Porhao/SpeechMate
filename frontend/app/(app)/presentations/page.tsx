"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Upload, FileText, Mic, Square, RotateCcw, Trash2, Loader2, ChevronRight,
  AlertTriangle, CheckCircle2, XCircle, ArrowRight, X,
} from "lucide-react";
import { presentationService, DECK_IN_PROGRESS } from "@/services/presentation";
import { useRecorder } from "@/hooks/useRecorder";
import type { BackendHealth, DeckListItem, NarratorVoices } from "@/types";
import { formatDate, formatDuration } from "@/utils/format";
import { tint, inkOf } from "@/lib/utils";

const ACCENT = "#8A5A22";

const STATUS_LABEL: Record<string, string> = {
  queued: "Queued",
  processing_slides: "Parsing slides",
  analyzing_content: "Analysing content",
  generating_scripts: "Writing scripts",
  synthesizing_audio: "Synthesizing voice",
  assembling_video: "Assembling video",
  complete: "Ready",
  failed: "Failed",
};

function StatusPill({ status }: { status: string }) {
  const color = status === "complete" ? "#3F6B4C" : status === "failed" ? "#8C3B32" : "#23345C";
  const Icon = status === "complete" ? CheckCircle2 : status === "failed" ? XCircle : Loader2;
  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full"
      style={{ background: `${tint(color, "14")}`, color, border: `1px solid ${tint(color, "28")}` }}
    >
      <Icon className={`w-3 h-3 ${DECK_IN_PROGRESS.has(status) ? "animate-spin" : ""}`} />
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}

export default function PresentationsPage() {
  const router = useRouter();
  const [decks, setDecks] = useState<DeckListItem[] | null>(null);
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [voices, setVoices] = useState<NarratorVoices | null>(null);
  const [narrator, setNarrator] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);

  const [pptx, setPptx] = useState<File | null>(null);
  const [voiceFile, setVoiceFile] = useState<File | null>(null);
  const [voiceMode, setVoiceMode] = useState<"none" | "record" | "upload">("none");
  const [requirement, setRequirement] = useState("");
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const rec = useRecorder();
  const pptxInput = useRef<HTMLInputElement>(null);
  const voiceInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      setDecks(await presentationService.list());
      setLoadError(null);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Couldn't load your presentations.");
    }
  }, []);

  useEffect(() => {
    presentationService.list()
      .then(setDecks)
      .catch((e: Error) => setLoadError(e.message));
    presentationService.health().then(setHealth).catch(() => null);
    presentationService.narratorVoices()
      .then((v) => { setVoices(v); setNarrator(v.default); })
      .catch(() => null);
  }, []);

  // Keep the list fresh while any deck is still generating.
  useEffect(() => {
    if (!decks?.some((d) => DECK_IN_PROGRESS.has(d.status))) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [decks, load]);

  const pickPptx = (file: File | undefined) => {
    if (!file) return;
    if (!/\.(pptx|pdf)$/i.test(file.name)) {
      setSubmitError("Please choose a PowerPoint (.pptx) or PDF file.");
      return;
    }
    setSubmitError(null);
    setPptx(file);
  };

  const voiceSample = voiceMode === "record" ? rec.blob : voiceMode === "upload" ? voiceFile : null;

  const submit = async () => {
    if (!pptx || submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const { session_id } = await presentationService.create(pptx, voiceSample, requirement, narrator || undefined);
      router.push(`/presentations/${session_id}`);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Upload failed.");
      setSubmitting(false);
    }
  };

  const remove = async (id: string) => {
    setConfirmDelete(null);
    try {
      await presentationService.remove(id);
      setDecks((d) => d?.filter((x) => x.session_id !== id) ?? null);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Delete failed.");
    }
  };

  const noAI = health && !health.llm.provider;

  return (
    <div className="px-4 sm:px-6 py-6 sm:py-8 max-w-[1100px] mx-auto space-y-6">
      <div>
        <h1 className="font-display text-2xl" style={{ color: "var(--ink)" }}>Presentation Coach</h1>
        <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
          Upload your slides. SpeechMate writes a script for each one and narrates the deck as an example
          presentation (in your own voice if you add a sample). Then you practise and get coached against it.
        </p>
      </div>

      {noAI && (
        <div
          className="flex items-start gap-3 text-sm px-4 py-3 rounded-xl"
          style={{ background: "rgba(138,90,34,0.07)", border: "1px solid rgba(138,90,34,0.25)", color: "#6B4419" }}
        >
          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>
            The backend has no LLM configured (<code>OPENAI_API_KEY</code>, or <code>LLM_BASE_URL</code> for a local
            model like Ollama), so scripts are built from the slide text and coach feedback is rule-based.
          </span>
        </div>
      )}

      {/* ── Stage 1: setup ─────────────────────────────────────────────── */}
      <div className="glass-card rounded-2xl p-5 sm:p-6 space-y-5">
        <h2 className="text-base font-semibold" style={{ color: "var(--ink)" }}>New presentation</h2>

        {/* PPTX drop zone */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => pptxInput.current?.click()}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") pptxInput.current?.click(); }}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); pickPptx(e.dataTransfer.files[0]); }}
          className="rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-colors"
          style={{
            border: `1.5px dashed ${dragging ? ACCENT : "var(--line-strong)"}`,
            background: dragging ? "rgba(138,90,34,0.05)" : "var(--bg)",
          }}
        >
          <input
            ref={pptxInput}
            type="file"
            accept=".pptx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation"
            className="hidden"
            onChange={(e) => pickPptx(e.target.files?.[0])}
          />
          {pptx ? (
            <div className="flex items-center gap-3">
              <FileText className="w-8 h-8" style={{ color: inkOf(ACCENT) }} />
              <div className="text-left">
                <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>{pptx.name}</p>
                <p className="text-xs" style={{ color: "var(--faint)" }}>{(pptx.size / 1024 / 1024).toFixed(1)} MB · click to change</p>
              </div>
            </div>
          ) : (
            <>
              <Upload className="w-7 h-7 mb-2" style={{ color: inkOf(ACCENT) }} />
              <p className="text-sm font-medium" style={{ color: "var(--ink)" }}>Drop a .pptx or .pdf here, or click to browse</p>
              <p className="text-xs mt-1" style={{ color: "var(--faint)" }}>Required</p>
            </>
          )}
        </div>

        {/* Narrator voice (local Malaysian TTS) */}
        {voices?.available && (
          <div>
            <label htmlFor="narrator" className="text-sm font-medium" style={{ color: "var(--ink)" }}>Narrator voice</label>
            <p className="text-xs mt-0.5 mb-2" style={{ color: "var(--muted)" }}>
              Open-source Malaysian TTS (Mesolitica). It handles Malay, English and code-switching, and runs on this server.
            </p>
            <select
              id="narrator"
              value={narrator}
              onChange={(e) => setNarrator(e.target.value)}
              className="text-sm px-3 py-2 rounded-lg outline-none"
              style={{ background: "var(--surface-2)", border: "1px solid var(--line)", color: "var(--ink)" }}
            >
              {voices.voices.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
            </select>
          </div>
        )}

        {/* Voice sample (cloning — optional, needs ElevenLabs) */}
        <div>
          <p className="text-sm font-medium mb-1" style={{ color: "var(--ink)" }}>Voice sample <span style={{ color: "var(--faint)" }}>(optional)</span></p>
          <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
            Only used for cloning your own voice, which needs an ElevenLabs key on the backend. Without one, the
            narrator voice above is used. For cloning, record 30–60 seconds of clear speech in a quiet room.
          </p>
          <div className="flex flex-wrap gap-2 mb-3">
            {(["none", "record", "upload"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setVoiceMode(m)}
                className="text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
                style={voiceMode === m
                  ? { background: ACCENT, color: "white" }
                  : { background: "var(--surface-2)", color: "var(--ink-2)", border: "1px solid var(--line)" }}
              >
                {m === "none" ? "Skip" : m === "record" ? "Record now" : "Upload file"}
              </button>
            ))}
          </div>

          {voiceMode === "record" && (
            <div className="rounded-xl p-4 space-y-3" style={{ background: "var(--surface-2)", border: "1px solid var(--line)" }}>
              <p className="text-xs italic" style={{ color: "var(--muted)" }}>
                Read aloud: &ldquo;Good morning everyone. Today I&rsquo;d like to walk you through an idea I&rsquo;ve been
                working on, why it matters, and what I think we should do next. Please stop me with questions at any point.&rdquo;
              </p>
              <div className="flex items-center gap-3 flex-wrap">
                {!rec.recording ? (
                  <button onClick={rec.start} className="flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-lg text-white" style={{ background: "#8C3B32" }}>
                    <Mic className="w-3.5 h-3.5" /> {rec.blob ? "Re-record" : "Start recording"}
                  </button>
                ) : (
                  <button onClick={rec.stop} className="flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-lg text-white" style={{ background: "#17181C" }}>
                    <Square className="w-3.5 h-3.5" /> Stop · {formatDuration(rec.seconds)}
                  </button>
                )}
                {rec.url && !rec.recording && <audio src={rec.url} controls className="h-9 max-w-full" />}
              </div>
              {rec.error && <p className="text-xs" style={{ color: "var(--bad)" }}>{rec.error}</p>}
            </div>
          )}

          {voiceMode === "upload" && (
            <div className="flex items-center gap-3">
              <input ref={voiceInput} type="file" accept="audio/*,.m4a,.webm,.ogg,.flac" className="hidden"
                onChange={(e) => setVoiceFile(e.target.files?.[0] ?? null)} />
              <button onClick={() => voiceInput.current?.click()} className="text-xs font-medium px-3 py-2 rounded-lg"
                style={{ background: "var(--surface-2)", border: "1px solid var(--line)", color: "var(--ink)" }}>
                Choose audio file
              </button>
              {voiceFile && (
                <span className="flex items-center gap-1 text-xs" style={{ color: "var(--ink-2)" }}>
                  {voiceFile.name}
                  <button onClick={() => setVoiceFile(null)} aria-label="Remove voice file"><X className="w-3 h-3" /></button>
                </span>
              )}
            </div>
          )}
        </div>

        {/* Requirement */}
        <div>
          <label htmlFor="requirement" className="text-sm font-medium" style={{ color: "var(--ink)" }}>
            Audience and purpose <span style={{ color: "var(--faint)" }}>(optional)</span>
          </label>
          <textarea
            id="requirement"
            value={requirement}
            onChange={(e) => setRequirement(e.target.value)}
            rows={2}
            placeholder="e.g. First-year students, non-specialist audience, 5-minute talk"
            className="mt-2 w-full px-3 py-2.5 rounded-xl text-sm outline-none resize-none placeholder:text-slate-400"
            style={{ background: "var(--surface-2)", border: "1px solid var(--line)", color: "var(--ink)" }}
          />
        </div>

        {submitError && <p className="text-sm" style={{ color: "var(--bad)" }}>{submitError}</p>}

        <button
          onClick={submit}
          disabled={!pptx || submitting || rec.recording}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-opacity disabled:opacity-40"
          style={{ background: ACCENT }}
        >
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
          {submitting ? "Uploading…" : "Generate example presentation"}
        </button>
      </div>

      {/* ── Past decks ─────────────────────────────────────────────────── */}
      <div className="glass-card rounded-2xl p-5 sm:p-6">
        <h2 className="text-base font-semibold mb-4" style={{ color: "var(--ink)" }}>Your presentations</h2>
        {loadError && (
          <div className="flex items-center gap-2 text-sm mb-3" style={{ color: "var(--bad)" }}>
            <AlertTriangle className="w-4 h-4" /> {loadError}
            <button onClick={load} className="ml-2 underline text-xs">Retry</button>
          </div>
        )}
        {decks === null && !loadError && <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--faint)" }} />}
        {decks?.length === 0 && <p className="text-sm" style={{ color: "var(--faint)" }}>No presentations yet. Upload a deck above to start.</p>}
        <div className="space-y-1">
          {decks?.map((d) => (
            <div key={d.session_id} className="flex items-center gap-3 p-3 rounded-xl hover:bg-[var(--surface-2)] transition-colors">
              <FileText className="w-5 h-5 flex-shrink-0" style={{ color: inkOf(ACCENT) }} />
              <Link href={`/presentations/${d.session_id}`} className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate" style={{ color: "var(--ink)" }}>{d.original_filename}</p>
                <p className="text-xs" style={{ color: "var(--faint)" }}>
                  {formatDate(d.created_at)}{d.slide_count ? ` · ${d.slide_count} slides` : ""}
                </p>
              </Link>
              <StatusPill status={d.status} />
              {confirmDelete === d.session_id ? (
                <span className="flex items-center gap-2 text-xs">
                  <button onClick={() => remove(d.session_id)} className="font-semibold" style={{ color: "var(--bad)" }}>Delete</button>
                  <button onClick={() => setConfirmDelete(null)} style={{ color: "var(--muted)" }}>Cancel</button>
                </span>
              ) : (
                <button
                  onClick={() => setConfirmDelete(d.session_id)}
                  disabled={DECK_IN_PROGRESS.has(d.status)}
                  className="p-1.5 rounded-lg disabled:opacity-30"
                  aria-label="Delete presentation"
                  title={DECK_IN_PROGRESS.has(d.status) ? "Wait for generation to finish" : "Delete"}
                >
                  <Trash2 className="w-4 h-4" style={{ color: "var(--faint)" }} />
                </button>
              )}
              <Link href={`/presentations/${d.session_id}`} aria-label="Open"><ChevronRight className="w-4 h-4" style={{ color: "var(--faint)" }} /></Link>
            </div>
          ))}
        </div>
        {decks && decks.length > 0 && (
          <button onClick={load} className="mt-3 flex items-center gap-1 text-xs" style={{ color: "var(--muted)" }}>
            <RotateCcw className="w-3 h-3" /> Refresh
          </button>
        )}
      </div>
    </div>
  );
}
