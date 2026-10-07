"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Upload, FileText, RotateCcw, Trash2, Loader2, ChevronRight,
  AlertTriangle, CheckCircle2, XCircle, ArrowRight,
} from "lucide-react";
import { presentationService, DECK_IN_PROGRESS } from "@/services/presentation";
import type { BackendHealth, DeckListItem } from "@/types";
import { formatDate } from "@/utils/format";
import { tint, inkOf } from "@/lib/utils";
import { PageHeader } from "@/components/ui/kit";
import ClayArt from "@/components/three/ClayArt";

const ACCENT = "#A8620F";

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
  const color = status === "complete" ? "#2F7A4F" : status === "failed" ? "#C2342C" : "#1A3A3A";
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
  const [loadError, setLoadError] = useState<string | null>(null);

  const [pptx, setPptx] = useState<File | null>(null);
  const [requirement, setRequirement] = useState("");
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const pptxInput = useRef<HTMLInputElement>(null);

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

  const submit = async () => {
    if (!pptx || submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const { session_id } = await presentationService.create(pptx, null, requirement);
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
      <PageHeader eyebrow="Presentation practice" title="Practise your talk and your Q&A" art={<ClayArt variant="present" className="h-[260px]" />}>
        <ol className="space-y-1.5">
          <li><b>1.</b> Upload your slides (.pptx or .pdf). The AI reads them: summary, structure and each slide&apos;s key point (about a minute).</li>
          <li><b>2.</b> Present it on camera, moving through your slides yourself. The AI checks that what you say on each slide matches what the slide is about, plus your voice and body language.</li>
          <li><b>3.</b> Rehearse the Q&amp;A: answer audience questions drawn from your own deck, with feedback on every answer.</li>
        </ol>
      </PageHeader>

      {noAI && (
        <div
          className="flex items-start gap-3 text-sm px-4 py-3 rounded-xl"
          style={{ background: "var(--surface-2)", border: "1px solid var(--line)", color: "var(--warn)" }}
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
          disabled={!pptx || submitting}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-opacity disabled:opacity-40"
          style={{ background: ACCENT }}
        >
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
          {submitting ? "Uploading…" : "Upload and prepare"}
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
