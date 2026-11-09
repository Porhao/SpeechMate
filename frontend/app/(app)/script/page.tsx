"use client";

// Script writer: pick a deck, say how long the talk is, and the AI writes what to say on each
// slide (word for word, or talking points), with the time each slide gets. "Practise this script"
// opens the deck's talk rehearsal with the script one tap away; the results add how much of it
// you kept and your time per slide against its plan.

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Check, Copy, Download, Loader2, PenLine, Presentation } from "lucide-react";
import { presentationService } from "@/services/presentation";
import { liveService } from "@/services/live";
import { authService } from "@/services/auth";
import SlideImage from "@/components/presentation/SlideImage";
import { Button, Card, Field, LinkButton, Notice, PageHeader, inputClass, inputStyle } from "@/components/ui/kit";
import { mascot } from "@/lib/mascot";
import { formatDuration } from "@/utils/format";
import type { DeckListItem, DeckScript, DeckStatusResponse, ScriptStyle } from "@/types";

const STYLES: { id: ScriptStyle; label: string; hint: string }[] = [
  { id: "full", label: "Full script", hint: "Word for word: read it aloud a few times, then loosen it" },
  { id: "points", label: "Talking points", hint: "An opening line, 2–3 points and a transition per slide" },
];

const asText = (deck: DeckStatusResponse, s: DeckScript) =>
  `${deck.original_filename.replace(/\.(pptx|pdf)$/i, "")}: ${s.minutes} min script\n\n` +
  s.slides.map((p) => `Slide ${p.slide_index} (${formatDuration(p.seconds)})\n${p.text}`).join("\n\n");

function ScriptWriter() {
  const router = useRouter();
  const params = useSearchParams();
  const [decks, setDecks] = useState<DeckListItem[] | null>(null);
  const [deckId, setDeckId] = useState(params.get("deck") ?? "");
  const [deck, setDeck] = useState<DeckStatusResponse | null>(null);
  const [minutes, setMinutes] = useState(5);
  const [style, setStyle] = useState<ScriptStyle>("full");
  const [writing, setWriting] = useState(false);
  const [starting, setStarting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authService.isSignedIn()) { router.push("/login?next=/script"); return; }
    presentationService.list()
      .then((all) => setDecks(all.filter((d) => d.status === "complete")))
      .catch((e: Error) => { setDecks([]); setError(e.message); });
  }, [router]);

  // The chosen deck, with its current script; the length starts at the deck's own estimate
  useEffect(() => {
    if (!deckId) return;
    let live = true;
    presentationService.get(deckId).then((d) => {
      if (!live) return;
      setDeck(d);
      if (d.script) { setMinutes(d.script.minutes); setStyle(d.script.style); }
      else if (d.insights?.stats) setMinutes(Math.max(1, Math.round((d.insights.stats.estimated_minutes[0] + d.insights.stats.estimated_minutes[1]) / 2)));
    }).catch((e: Error) => setError(e.message));
    return () => { live = false; };
  }, [deckId]);

  const write = async () => {
    if (!deck) return;
    setWriting(true); setError(null); mascot("busy", "Writing your script…");
    try {
      const script = await presentationService.writeScript(deck.session_id, minutes, style);
      setDeck({ ...deck, script });
      mascot("success", "Your script is ready. Read it aloud once before you practise.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't write the script"); mascot("error");
    } finally { setWriting(false); }
  };

  const practise = async () => {
    if (!deck) return;
    setStarting(true); setError(null);
    try {
      const s = await liveService.start({ session_type: "Presentation", deck_id: deck.session_id, presentation_mode: "talk", use_script: true });
      router.push(`/session?mode=Presentation&live=${s.id}`);
    } catch (e) { setError(e instanceof Error ? e.message : "Couldn't start the session"); setStarting(false); }
  };

  const copy = async () => {
    if (!deck?.script) return;
    try { await navigator.clipboard.writeText(asText(deck, deck.script)); setCopied(true); setTimeout(() => setCopied(false), 1500); }
    catch { setError("Couldn't copy: select the text and copy it instead."); }
  };

  const download = () => {
    if (!deck?.script) return;
    const url = URL.createObjectURL(new Blob([asText(deck, deck.script)], { type: "text/plain" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: `${deck.original_filename.replace(/\.(pptx|pdf)$/i, "")} script.txt` });
    a.click(); URL.revokeObjectURL(url);
  };

  const script = deck?.session_id === deckId ? deck.script : null;
  const words = script?.slides.reduce((n, p) => n + p.text.split(/\s+/).filter(Boolean).length, 0) ?? 0;

  return (
    <div className="px-4 sm:px-6 py-6 max-w-[1000px] mx-auto space-y-5">
      <PageHeader eyebrow="Script writer" title="Write a script from your slides">
        Choose a deck and how long you have. The AI writes what to say on each slide, using only what&apos;s on your slides,
        and plans how long to spend on each. Then practise it.
      </PageHeader>

      {error && <Notice tone="bad">{error}</Notice>}

      <Card title="Your script">
        {decks === null ? <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--faint)" }} />
          : decks.length === 0 ? (
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-sm flex-1" style={{ color: "var(--ink-2)" }}>Upload a deck first. Once it&apos;s been read, it shows up here.</p>
              <LinkButton href="/presentations">Upload a deck</LinkButton>
            </div>
          ) : (
            <div className="grid sm:grid-cols-[1fr_140px] gap-4">
              <Field label="Deck">
                <select className={inputClass} style={inputStyle} value={deckId}
                  onChange={(e) => { setDeckId(e.target.value); setDeck(null); router.replace(`/script?deck=${e.target.value}`); }}>
                  <option value="" disabled>Choose a deck…</option>
                  {decks.map((d) => <option key={d.session_id} value={d.session_id}>{d.original_filename}{d.slide_count ? ` (${d.slide_count} slides)` : ""}</option>)}
                </select>
              </Field>
              <Field label="Talk length" hint="minutes">
                <input type="number" min={1} max={60} step={0.5} className={inputClass} style={inputStyle} value={minutes}
                  onChange={(e) => setMinutes(Math.min(60, Math.max(1, Number(e.target.value) || 1)))} />
              </Field>
              <div className="sm:col-span-2 flex flex-wrap gap-2" role="radiogroup" aria-label="Script style">
                {STYLES.map((s) => (
                  <button key={s.id} role="radio" aria-checked={style === s.id} onClick={() => setStyle(s.id)}
                    className={`nav-pill text-left px-4 py-2.5 rounded-lg ${style === s.id ? "nav-pill-active" : ""}`}>
                    <span className="block text-sm font-semibold">{s.label}</span>
                    <span className="block text-xs opacity-75">{s.hint}</span>
                  </button>
                ))}
              </div>
              <div className="sm:col-span-2">
                <Button onClick={write} disabled={!deck || writing}>
                  {writing ? <Loader2 className="w-4 h-4 animate-spin" /> : <PenLine className="w-4 h-4" />}
                  {writing ? "Writing…" : script ? "Rewrite the script" : "Write my script"}
                </Button>
              </div>
            </div>
          )}
      </Card>

      {deck && script && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <p className="flex-1 text-sm" style={{ color: "var(--ink-2)" }}>
              <b style={{ color: "var(--ink)" }}>{script.minutes} min</b> · {script.slides.length} slides · about {words} words
              {script.style === "points" ? " of talking points" : ` (~${script.wpm} words a minute)`}
            </p>
            <Button variant="secondary" onClick={copy}>{copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />} {copied ? "Copied" : "Copy"}</Button>
            <Button variant="secondary" onClick={download}><Download className="w-4 h-4" /> Download</Button>
            <Button onClick={practise} disabled={starting}>
              {starting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Presentation className="w-4 h-4" />} Practise this script
            </Button>
          </div>

          {script.source === "rules" && (
            <Notice tone="warn">The AI wasn&apos;t available, so this is built straight from your slides&apos; text. Try “Rewrite” later for a proper script.</Notice>
          )}
          {script.style === "full" && script.read_sec != null && Math.abs(script.read_sec - script.minutes * 60) > script.minutes * 9 && (
            <Notice tone="warn">
              Read at a normal pace this script takes about {formatDuration(script.read_sec)}, not {formatDuration(script.minutes * 60)}.
              {script.read_sec < script.minutes * 60 ? " Add your own examples where it's thin, or press Rewrite." : " Trim it, or press Rewrite."}
            </Notice>
          )}
          {script.unverified_terms.length > 0 && (
            <Notice tone="warn">Check these before you say them; they aren&apos;t on your slides: {script.unverified_terms.join(", ")}.</Notice>
          )}

          <ol className="space-y-4">
            {script.slides.map((p) => (
              <li key={p.slide_index} className="grid sm:grid-cols-[220px_1fr] gap-4 p-4 rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--line)" }}>
                <SlideImage deckId={deck.session_id} n={p.slide_index} alt={`Slide ${p.slide_index}`}
                  className="w-full aspect-video object-contain rounded-md" style={{ background: "var(--surface-2)" }} />
                <div className="min-w-0">
                  <p className="text-xs font-semibold tabular-nums mb-1.5" style={{ color: "var(--muted)" }}>
                    Slide {p.slide_index} · about {formatDuration(p.seconds)}
                  </p>
                  <p className="text-[15px] leading-relaxed whitespace-pre-line" style={{ color: "var(--ink)" }}>{p.text}</p>
                </div>
              </li>
            ))}
          </ol>

          <p className="text-xs" style={{ color: "var(--muted)" }}>
            Tip: read it aloud two or three times, then practise with the script hidden (“Show my script” is one tap away
            during the talk). Your talk is judged on what each slide means, not on reciting every word.{" "}
            <Link href={`/presentations/${deck.session_id}`} className="underline">Open the deck</Link>
          </p>
        </>
      )}
    </div>
  );
}

export default function ScriptPage() {
  return <Suspense fallback={null}><ScriptWriter /></Suspense>;
}
