"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Upload, FileText, RotateCcw, Loader2, ChevronRight,
  AlertTriangle, CheckCircle2, XCircle, ArrowRight, LayoutGrid, List as ListIcon,
} from "lucide-react";
import { presentationService, DECK_IN_PROGRESS } from "@/services/presentation";
import { liveService } from "@/services/live";
import type { BackendHealth, DeckListItem, DeckStatusResponse, LiveSession } from "@/types";
import { formatDate } from "@/utils/format";
import { tint, inkOf } from "@/lib/utils";
import { mascot } from "@/lib/mascot";
import { STAGES, deckProgress, type DeckProgress } from "@/lib/deckPipeline";
import { useExit } from "@/hooks/useExit";
import { PageHeader } from "@/components/ui/kit";
import { SearchBar, Highlight, matches } from "@/components/ui/SearchBar";
import UploadCard, { type UploadPhase } from "@/components/ui/UploadCard";
import HoopShot, { type HoopStep } from "@/components/ui/HoopShot";
import ClayArt from "@/components/three/ClayArt";
import DeleteButton from "@/components/ui/DeleteButton";

const ACCENT = "#A8620F";

// The deck's preparation as steps on the hoop's backboard (the same steps as GenerationProgress)
function prepSteps(d: DeckStatusResponse | null): HoopStep[] {
  const reading = !d || d.status === "queued" || d.status === "processing_slides";
  const done = d?.status === "complete" || d?.status === "failed";
  return [
    { label: d?.status === "queued" ? "Waiting in the queue" : "Reading your slides", state: reading ? "active" : "done",
      count: d?.slide_count ? `${d.slides_rendered}/${d.slide_count}` : undefined },
    { label: "Understanding them: summary, key points, Q&A", state: done ? "done" : reading ? "todo" : "active" },
  ];
}

// How full the net is: the upload is the first 40%, reading the slides the next 40%, then understanding them
function netFill(phase: UploadPhase, progress: number | null, d: DeckStatusResponse | null): number {
  if (phase === "idle") return 0;
  if (phase === "done") return 1;
  if (phase === "uploading" || !d) return 0.4 * (progress ?? 0);
  if (d.status === "analyzing_content") return 0.85;
  return 0.4 + 0.4 * (d.slide_count ? d.slides_rendered / d.slide_count : 0);
}

const STATUS_LABEL: Record<string, string> = {
  queued: "Queued",
  processing_slides: "Reading slides",
  analyzing_content: "Understanding them",
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

/** One deck on the board: its stage colour, how far along it is, and its best score. */
function BoardCard({ p, query, leaving, onDelete }: { p: DeckProgress; query: string; leaving: boolean; onDelete: () => void }) {
  const stage = STAGES[p.step - 1];
  const failed = p.deck.status === "failed";
  return (
    <li className={`row-in ${leaving ? "row-exit" : ""}`}>
      {/* The title is a link stretched over the whole card; the bin sits above it */}
      <div className="clay relative rounded-xl p-4 transition-transform hover:-translate-y-0.5 focus-within:-translate-y-0.5"
        style={{ background: stage.bg, color: stage.fg }}>
        <div className="flex items-start gap-2">
          <p className="flex-1 min-w-0 text-[11px] font-medium opacity-75">
            {p.lastAt ? `Last practised ${formatDate(p.lastAt)}` : `Uploaded ${formatDate(p.deck.created_at)}`}
          </p>
          <span className="relative z-10">
            <DeleteButton disabled={DECK_IN_PROGRESS.has(p.deck.status)} onDelete={onDelete} light={stage.fg === "#FFFFFF"} label="Delete presentation" />
          </span>
        </div>
        <Link href={`/presentations/${p.deck.session_id}`} className="block font-semibold leading-snug mt-1 break-words outline-none after:absolute after:inset-0 after:rounded-xl focus-visible:after:ring-2 focus-visible:after:ring-[var(--accent-ink)]">
          <Highlight text={p.deck.original_filename} query={query} />
        </Link>
        <p className="text-xs mt-1 opacity-80">
          {p.deck.slide_count ? `${p.deck.slide_count} slides` : STATUS_LABEL[p.deck.status] ?? p.deck.status}
          {p.talks ? ` · presented ${p.talks}×` : ""}{p.rehearsals ? ` · Q&A ${p.rehearsals}×` : ""}
        </p>
        <div className="mt-3 flex items-center gap-3">
          {/* How far along the four stages */}
          <span className="flex-1 flex gap-1" role="img" aria-label={`Stage ${p.step} of 4`}>
            {STAGES.map((s, i) => (
              <span key={s.id} className="h-1.5 flex-1 rounded-full" style={{ background: i < p.step ? "currentColor" : "color-mix(in srgb, currentColor 22%, transparent)" }} />
            ))}
          </span>
          <span className="font-display text-xl tabular-nums leading-none" aria-label={p.best != null ? `Best score ${p.best}` : undefined}>{failed ? "!" : p.best ?? "—"}</span>
        </div>
        {failed && <p className="text-[11px] font-semibold mt-2" style={{ color: "var(--bad)" }}>Preparing failed: open it to retry</p>}
      </div>
    </li>
  );
}

export default function PresentationsPage() {
  const router = useRouter();
  const [decks, setDecks] = useState<DeckListItem[] | null>(null);
  const [sessions, setSessions] = useState<LiveSession[]>([]);
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [pptx, setPptx] = useState<File | null>(null);
  const [requirement, setRequirement] = useState("");
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [progress, setProgress] = useState<number | null>(null);
  // After the upload: the deck being read, followed on the hoop until it's ready
  const [prep, setPrep] = useState<DeckStatusResponse | null>(null);
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [view, setView] = useState<"board" | "list">("board");
  const { isLeaving, exit } = useExit();

  const pptxInput = useRef<HTMLInputElement>(null);
  const submitting = phase !== "idle";

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
    liveService.history().then(setSessions).catch(() => null);  // for each deck's stage
    presentationService.health().then(setHealth).catch(() => null);
  }, []);

  // Keep the list fresh while any deck is still being prepared.
  useEffect(() => {
    if (!decks?.some((d) => DECK_IN_PROGRESS.has(d.status))) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [decks, load]);

  const pickPptx = (file: File | undefined) => {
    if (!file || submitting) return;
    if (!/\.(pptx|pdf)$/i.test(file.name)) {
      setSubmitError("Please choose a PowerPoint (.pptx) or PDF file.");
      mascot("error", "That one isn't a .pptx or .pdf.");
      return;
    }
    setSubmitError(null);
    setPptx(file);
  };

  const submit = async () => {
    if (!pptx || submitting) return;
    setPhase("uploading"); setProgress(0);
    setSubmitError(null);
    mascot("busy", "Uploading your deck…");
    try {
      const { session_id } = await presentationService.create(pptx, requirement, (f) => {
        setProgress(f);
        if (f >= 1) setPhase("processing");
      });
      mascot("success", "Got it! I'm reading your slides now.");
      // Follow its preparation on the hoop, then open it (its page shows a failure and Retry)
      const follow = async () => {
        if (!alive.current) return;
        try {
          const d = await presentationService.get(session_id);
          setPrep(d);
          if (DECK_IN_PROGRESS.has(d.status)) { setTimeout(follow, 1500); return; }
        } catch { /* the deck page will show what happened */ }
        if (!alive.current) return;
        setPhase("done");
        setTimeout(() => alive.current && router.push(`/presentations/${session_id}`), 900);  // let the check pop
      };
      follow();
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Upload failed.");
      setPhase("idle"); setProgress(null);
      mascot("error");
    }
  };

  const remove = async (id: string) => {
    try {
      await presentationService.remove(id);
      exit(id, () => setDecks((d) => d?.filter((x) => x.session_id !== id) ?? null));
      mascot("deleted", "Deck deleted.");
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Delete failed.");
      mascot("error");
    }
  };

  const shown = useMemo(() => (decks ?? []).filter((d) => matches(query, d.original_filename)), [decks, query]);
  const board = useMemo(() => shown.map((d) => deckProgress(d, sessions)), [shown, sessions]);
  const noAI = health && !health.llm.provider;

  return (
    <div className="px-4 sm:px-6 py-6 max-w-[1100px] mx-auto space-y-5">
      <PageHeader eyebrow="Presentation practice" title="Practise your talk and your Q&A" art={<ClayArt variant="present" className="h-[200px]" />}>
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
            The backend has no LLM configured (<code>LLM_BASE_URL</code> / <code>LLM_API_KEY</code>), so the deck insights
            come from the slide text and the Q&amp;A uses a standard question set.
          </span>
        </div>
      )}

      {/* ── Upload ─────────────────────────────────────────────────────── */}
      <div className="glass-card rounded-2xl p-5 sm:p-6 space-y-5">
        <h2 className="text-base font-semibold" style={{ color: "var(--ink)" }}>New presentation</h2>

        {/* Drop zone: pulses while a file is dragged over it */}
        <div
          role="button"
          tabIndex={0}
          aria-disabled={submitting}
          onClick={() => !submitting && pptxInput.current?.click()}
          onKeyDown={(e) => { if (!submitting && (e.key === "Enter" || e.key === " ")) pptxInput.current?.click(); }}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); pickPptx(e.dataTransfer.files[0]); }}
          className={`rounded-xl p-6 flex flex-col items-center justify-center text-center transition-colors ${submitting ? "" : "cursor-pointer"} ${dragging ? "drop-hot" : ""}`}
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
            <UploadCard name={pptx.name} size={pptx.size} phase={phase} progress={progress} color={inkOf(ACCENT)}
              processingLabel={prepSteps(prep).find((x) => x.state === "active")?.label ?? "Uploaded. Starting to read your slides…"} />
          ) : (
            <>
              <Upload className={`w-7 h-7 mb-2 transition-transform ${dragging ? "-translate-y-1 scale-110" : ""}`} style={{ color: inkOf(ACCENT) }} />
              <p className="text-sm font-medium" style={{ color: "var(--ink)" }}>{dragging ? "Drop it here" : "Drop a .pptx or .pdf here, or click to browse"}</p>
              <p className="text-xs mt-1" style={{ color: "var(--faint)" }}>Required</p>
            </>
          )}
        </div>

        <div>
          <label htmlFor="requirement" className="text-sm font-medium" style={{ color: "var(--ink)" }}>
            Audience and purpose <span style={{ color: "var(--faint)" }}>(optional)</span>
          </label>
          <textarea
            id="requirement"
            value={requirement}
            onChange={(e) => setRequirement(e.target.value)}
            rows={2}
            disabled={submitting}
            placeholder="e.g. First-year students, non-specialist audience, 5-minute talk"
            className="mt-2 w-full px-3 py-2.5 rounded-xl text-sm outline-none resize-none placeholder:text-slate-400"
            style={{ background: "var(--surface-2)", border: "1px solid var(--line)", color: "var(--ink)" }}
          />
        </div>

        {/* The fun way in: shoot the file into the hoop (the button below does the same); the
            hoop then shows the upload's progress */}
        {pptx && (
          <HoopShot key={pptx.name + pptx.size} label={pptx.name.toLowerCase().endsWith(".pdf") ? "PDF" : "PPTX"} fileName={pptx.name}
            color={inkOf(ACCENT)} onScore={submit} status={phase} progress={progress} processingLabel="Preparing your deck"
            steps={prepSteps(prep)} fill={netFill(phase, progress, prep)} />
        )}

        {submitError && <p className="text-sm" style={{ color: "var(--bad)" }}>{submitError}</p>}

        <button
          onClick={submit}
          disabled={!pptx || submitting}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-opacity disabled:opacity-40"
          style={{ background: ACCENT }}
        >
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
          {phase === "uploading" ? "Uploading…" : phase === "idle" ? "Upload and prepare" : "Opening your deck…"}
        </button>
      </div>

      {/* ── Your decks: a pipeline board, or a list ───────────────────── */}
      <div className="glass-card rounded-2xl p-5 sm:p-6">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <h2 className="text-base font-semibold mr-auto" style={{ color: "var(--ink)" }}>Your presentations</h2>
          {decks && decks.length > 0 && (
            <>
              <SearchBar value={query} onChange={setQuery} placeholder="Search your decks…" results={shown.length} label="Search your presentations" />
              <div role="tablist" aria-label="View" className="inline-flex p-1 gap-1 rounded-full" style={{ background: "var(--surface-3)" }}>
                {([["board", "Board", LayoutGrid], ["list", "List", ListIcon]] as const).map(([id, label, Icon]) => (
                  <button key={id} role="tab" aria-selected={view === id} onClick={() => setView(id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors"
                    style={{ background: view === id ? "var(--surface)" : "transparent", color: view === id ? "var(--ink)" : "var(--muted)", boxShadow: view === id ? "var(--shadow-card)" : "none" }}>
                    <Icon className="w-3.5 h-3.5" /> {label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
        {loadError && (
          <div className="flex items-center gap-2 text-sm mb-3" style={{ color: "var(--bad)" }}>
            <AlertTriangle className="w-4 h-4" /> {loadError}
            <button onClick={load} className="ml-2 underline text-xs">Retry</button>
          </div>
        )}
        {decks === null && !loadError && <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--faint)" }} />}
        {decks?.length === 0 && <p className="text-sm" style={{ color: "var(--faint)" }}>No presentations yet. Upload a deck above to start.</p>}
        {decks && decks.length > 0 && shown.length === 0 && (
          <p className="text-sm py-6 text-center" style={{ color: "var(--muted)" }}>No deck matches &ldquo;{query}&rdquo;.</p>
        )}

        {view === "board" && shown.length > 0 && (
          <div className="flex gap-4 overflow-x-auto pb-2 -mx-1 px-1 snap-x">
            {STAGES.map((stage) => {
              const cards = board.filter((p) => p.stage === stage.id);
              return (
                <section key={stage.id} className="snap-start flex-shrink-0 w-[240px] sm:w-auto sm:flex-1 sm:min-w-[200px] rounded-xl p-2.5"
                  style={{ background: "var(--surface-2)", border: "1px solid var(--line-2)" }} aria-label={stage.label}>
                  <header className="flex items-center gap-2 px-1.5 pb-2.5">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ background: stage.bg, border: "1px solid var(--line)" }} />
                    <h3 className="text-sm font-semibold" style={{ color: "var(--ink)" }}>{stage.label}</h3>
                    <span className="text-[11px] font-semibold px-1.5 rounded-full tabular-nums" style={{ background: "var(--surface-3)", color: "var(--ink-2)" }}>{cards.length}</span>
                  </header>
                  <p className="px-1.5 -mt-1.5 pb-2.5 text-[11px]" style={{ color: "var(--muted)" }}>{stage.hint}</p>
                  <ul className="space-y-2.5">
                    {cards.map((p) => (
                      <BoardCard key={p.deck.session_id} p={p} query={query} leaving={isLeaving(p.deck.session_id)}
                        onDelete={() => remove(p.deck.session_id)} />
                    ))}
                    {cards.length === 0 && <li className="text-xs px-1.5 py-3 text-center rounded-lg" style={{ color: "var(--faint)", border: "1px dashed var(--line)" }}>Nothing here</li>}
                  </ul>
                </section>
              );
            })}
          </div>
        )}

        {view === "list" && (
          <ul className="space-y-1">
            {board.map((p) => {
              const d = p.deck;
              return (
                <li key={d.session_id} className={`row-in flex items-center gap-3 p-3 rounded-xl hover:bg-[var(--surface-2)] transition-colors ${isLeaving(d.session_id) ? "row-exit" : ""}`}>
                  <FileText className="w-5 h-5 flex-shrink-0" style={{ color: inkOf(ACCENT) }} />
                  <Link href={`/presentations/${d.session_id}`} className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: "var(--ink)" }}><Highlight text={d.original_filename} query={query} /></p>
                    <p className="text-xs" style={{ color: "var(--faint)" }}>
                      {formatDate(d.created_at)}{d.slide_count ? ` · ${d.slide_count} slides` : ""} · {STAGES[p.step - 1].label}
                    </p>
                  </Link>
                  <StatusPill status={d.status} />
                  <DeleteButton disabled={DECK_IN_PROGRESS.has(d.status)} onDelete={() => remove(d.session_id)} label="Delete presentation" />
                  <Link href={`/presentations/${d.session_id}`} aria-label="Open"><ChevronRight className="w-4 h-4" style={{ color: "var(--faint)" }} /></Link>
                </li>
              );
            })}
          </ul>
        )}

        {decks && decks.length > 0 && (
          <button onClick={load} className="mt-3 flex items-center gap-1 text-xs" style={{ color: "var(--muted)" }}>
            <RotateCcw className="w-3 h-3" /> Refresh
          </button>
        )}
      </div>
    </div>
  );
}
