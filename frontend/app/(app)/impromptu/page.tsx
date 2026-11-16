"use client";

// Impromptu speaking: pick a theme, spin for a random topic, research it for 5 minutes, then talk
// about it for 1-2 minutes. The talk is transcribed and judged on how well you understood the topic.

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FlaskConical, Gamepad2, GraduationCap, Loader2, Mic, Search, Sparkles, Square } from "lucide-react";
import { conversationService, impromptuService, type ImpromptuResult } from "@/services/live";
import { ApiError } from "@/services/api";
import { Button, Card, Dots, Notice, PageHeader, inputClass, inputStyle } from "@/components/ui/kit";
import { formatDuration } from "@/lib/format";
import { requireSignIn } from "@/hooks/useAuth";

const THEMES = [
  { name: "Games", icon: Gamepad2, topics: [
    "How video games can teach problem-solving",
    "Should esports count as a real sport?",
    "Why some mobile games are so hard to put down",
    "Are video games good or bad for children?",
  ] },
  { name: "Education", icon: GraduationCap, topics: [
    "Online classes versus classroom learning",
    "Should university education be free?",
    "How AI tools are changing homework",
    "Why learning a second language matters",
  ] },
  { name: "Science", icon: FlaskConical, topics: [
    "Why the sky is blue",
    "How vaccines train the immune system",
    "What causes climate change, and what can we do?",
    "How electric cars work",
  ] },
  { name: "Anything", icon: Sparkles, topics: [
    "Why sleep matters more than you think",
    "The most important invention of the last 100 years",
    "How social media changes friendships",
    "What makes a good leader",
  ] },
] as const;

const RESEARCH_SEC = 5 * 60, TALK_SEC = 2 * 60, MIN_TALK_SEC = 60;
type Phase = "choose" | "research" | "speak" | "judging" | "result";


export default function ImpromptuPage() {
  const router = useRouter();
  const [theme, setTheme] = useState(0);
  const [topic, setTopic] = useState<string | null>(null);
  const [reel, setReel] = useState(0);              // index shown in the slot window
  const [spinning, setSpinning] = useState(false);
  const [phase, setPhase] = useState<Phase>("choose");
  const [endsAt, setEndsAt] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImpromptuResult | null>(null);
  const [transcript, setTranscript] = useState("");
  const streamRef = useRef<MediaStream | null>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const talkStartRef = useRef(0);
  const spinTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [lastTalk, setLastTalk] = useState<{ blob: Blob; seconds: number } | null>(null);  // for "Try again"

  const topics = THEMES[theme].topics;
  const left = Math.max(0, (endsAt - now) / 1000);
  const talked = TALK_SEC - left;  // only read while talking

  // One clock for both countdowns
  useEffect(() => {
    if (phase !== "research" && phase !== "speak") return;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [phase]);

  // Release the mic and timers when leaving the page
  useEffect(() => () => {
    if (spinTimer.current) clearTimeout(spinTimer.current);
    if (recRef.current?.state === "recording") { recRef.current.onstop = null; recRef.current.stop(); }
    streamRef.current?.getTracks().forEach((t) => t.stop());
  }, []);

  const spin = () => {
    if (spinning) return;
    // A different topic from the current one when there is one
    const pool = topics.map((_, i) => i).filter((i) => topics[i] !== topic);
    const target = pool[Math.floor(Math.random() * pool.length)];
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setReel(target); setTopic(topics[target]); return; }
    setSpinning(true); setTopic(null);
    // Slot-machine reel: ~3 turns that slow down and land on the target
    const steps = topics.length * 3 + ((target - reel + topics.length) % topics.length);
    let i = 0;
    const tick = () => {
      i++;
      setReel((r) => (r + 1) % topics.length);
      if (i >= steps) { setSpinning(false); setTopic(topics[target]); return; }
      spinTimer.current = setTimeout(tick, 50 + 260 * (i / steps) ** 3);
    };
    tick();
  };

  const startResearch = async () => {
    if (!requireSignIn(router)) return;
    setError(null);
    try {
      // Ask for the mic now, so the talk can start on its own when the research time is up
      streamRef.current ??= await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("SpeechMate needs your microphone for this. Allow it in the browser and press Start again.");
      return;
    }
    setNotes(""); setResult(null); setTranscript("");
    setNow(Date.now()); setEndsAt(Date.now() + RESEARCH_SEC * 1000); setPhase("research");
  };

  const judge = async (blob: Blob, seconds: number) => {
    setPhase("judging"); setError(null);
    try {
      const text = transcript || await conversationService.transcribe(blob, topic!);
      setTranscript(text);
      setResult(await impromptuService.evaluate(topic!, text, seconds));
      setPhase("result");
    } catch (e) {
      setError(e instanceof ApiError && e.status === 503 ? "The AI judge isn't available right now. Please try again later."
        : "Couldn't judge your talk. Check your connection and try again.");
      setLastTalk({ blob, seconds });
      setPhase("result");
    }
  };
  const startTalk = () => {
    const stream = streamRef.current;
    if (!stream) return;
    const rec = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
    rec.onstop = () => {
      stream.getTracks().forEach((t) => t.stop()); streamRef.current = null;  // mic off as soon as you finish
      const type = rec.mimeType || "audio/webm";
      const seconds = Math.min(TALK_SEC, (Date.now() - talkStartRef.current) / 1000);
      void judge(new Blob(chunks, { type }), seconds);
    };
    rec.start();
    recRef.current = rec;
    talkStartRef.current = Date.now();
    setNow(Date.now()); setEndsAt(Date.now() + TALK_SEC * 1000); setPhase("speak");
  };
  const finishTalk = () => { if (recRef.current?.state === "recording") recRef.current.stop(); };

  // Time's up: research → talk, talk → judge
  useEffect(() => {
    if (left > 0) return;
    if (phase === "research") startTalk();
    else if (phase === "speak") finishTalk();
  }, [left, phase]); // eslint-disable-line react-hooks/exhaustive-deps

  const reset = (keepTopic: boolean) => {
    if (!keepTopic) setTopic(null);
    setLastTalk(null); setResult(null); setError(null); setTranscript(""); setPhase("choose");
  };

  // ── Choose a theme and spin ───────────────────────────────────────────────
  if (phase === "choose") return (
    <div className="px-4 sm:px-6 py-6 max-w-[900px] mx-auto">
      <PageHeader eyebrow="Impromptu speaking" title="Spin a topic. Research it. Talk about it.">
        Pick a theme and spin for a random topic. You get 5 minutes to research it, then 1–2 minutes to explain it
        out loud. Afterwards SpeechMate checks how well you understood and explained the topic.
      </PageHeader>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5" role="radiogroup" aria-label="Theme">
        {THEMES.map(({ name, icon: Icon }, i) => (
          <button key={name} role="radio" aria-checked={theme === i} disabled={spinning}
            onClick={() => { setTheme(i); setTopic(null); setReel(0); }}
            className="p-4 rounded-lg flex flex-col items-center gap-2 text-sm font-semibold transition-colors disabled:opacity-60"
            style={{ background: theme === i ? "var(--surface-2)" : "var(--surface)", color: "var(--ink)",
                     border: `1px solid ${theme === i ? "var(--accent-ink)" : "var(--line)"}` }}>
            <Icon className="w-6 h-6" style={{ color: "var(--accent-ink)" }} /> {name}
          </button>
        ))}
      </div>
      <Card>
        {/* The slot window: the reel's previous, current and next topics, the middle one in focus */}
        <div className="relative rounded-md overflow-hidden mb-4" style={{ background: "var(--surface-2)", border: "1px solid var(--line-strong)" }}
          aria-live="polite">
          {[-1, 0, 1].map((d) => (
            <p key={d} className={d === 0 ? "py-4 px-4 text-center text-lg font-semibold" : "py-1.5 px-4 text-center text-xs truncate"}
              style={{ color: d === 0 ? "var(--ink)" : "var(--faint)", borderBlock: d === 0 ? "1px solid var(--line)" : undefined }}
              aria-hidden={d !== 0 || spinning}>
              {topic && d === 0 ? topic : topics[(reel + d + topics.length) % topics.length]}
            </p>
          ))}
        </div>
        {topic && !spinning && <p className="sr-only">Your topic: {topic}</p>}
        <div className="flex flex-col sm:flex-row gap-3">
          <Button variant={topic ? "secondary" : "primary"} className="flex-1" onClick={spin} disabled={spinning}>
            {spinning ? "Spinning…" : topic ? "Spin again" : "Spin"}
          </Button>
          <Button className="flex-1" onClick={startResearch} disabled={!topic || spinning}>Start: 5 minutes to research</Button>
        </div>
        {error && <div className="mt-4"><Notice tone="bad">{error}</Notice></div>}
      </Card>
    </div>
  );

  // ── Research, then talk ───────────────────────────────────────────────────
  if (phase === "research" || phase === "speak") {
    const talking = phase === "speak";
    return (
      <div className="px-4 sm:px-6 py-6 max-w-[900px] mx-auto space-y-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] mb-2" style={{ color: "var(--muted)" }}>
            {talking ? "Your talk" : "Research time"} · {THEMES[theme].name}
          </p>
          <h1 className="font-display text-3xl sm:text-4xl leading-[1.08]" style={{ color: "var(--ink)" }}>{topic}</h1>
        </div>
        <Card>
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div role="timer" aria-live="off">
              <p className="text-5xl font-semibold tabular-nums" style={{ color: talking && left < 15 ? "var(--bad)" : "var(--ink)" }}>{formatDuration(left)}</p>
              <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
                {talking ? (talked < MIN_TALK_SEC ? `Keep going: at least ${formatDuration(MIN_TALK_SEC - talked)} more` : "You can finish any time")
                         : "Your talk starts automatically when the time is up"}
              </p>
            </div>
            {talking ? (
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1.5 text-sm font-semibold" style={{ color: "var(--bad)" }}>
                  <Mic className="w-4 h-4" /> Recording
                </span>
                <Button onClick={finishTalk} disabled={talked < MIN_TALK_SEC}><Square className="w-4 h-4" /> Finish</Button>
              </div>
            ) : (
              <div className="flex gap-3 flex-wrap">
                <a href={`https://www.google.com/search?q=${encodeURIComponent(topic ?? "")}`} target="_blank" rel="noreferrer"
                  className="inline-flex items-center gap-2 h-11 px-5 rounded-md text-sm font-semibold"
                  style={{ border: "1px solid var(--line-strong)", color: "var(--ink)" }}>
                  <Search className="w-4 h-4" /> Search the web
                </a>
                <Button onClick={startTalk}><Mic className="w-4 h-4" /> I&apos;m ready, start talking</Button>
              </div>
            )}
          </div>
        </Card>
        <Card title={talking ? "Your notes" : "Notes (only you see these)"}>
          {!talking && (
            <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
              Aim for: what it is · how or why it works · one example · your own view. Keep the notes to a few words each.
            </p>
          )}
          <textarea className={inputClass} style={{ ...inputStyle, minHeight: 140 }} value={notes} readOnly={talking}
            aria-label="Notes" maxLength={1500} onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. sunlight = all colours → air scatters blue most → sunsets red (longer path)" />
        </Card>
      </div>
    );
  }

  // ── Judging and the result ────────────────────────────────────────────────
  if (phase === "judging") return (
    <div className="px-4 py-24 flex flex-col items-center gap-3" role="status">
      <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--accent-ink)" }} />
      <p className="text-sm" style={{ color: "var(--ink-2)" }}>Listening back to your talk and checking your understanding…</p>
    </div>
  );

  const r = result;
  const list = (title: string, items?: string[]) => items && items.length > 0 && (
    <Card title={title}>
      <ul className="space-y-1.5 list-disc pl-5 text-sm" style={{ color: "var(--ink-2)" }}>
        {items.map((x) => <li key={x}>{x}</li>)}
      </ul>
    </Card>
  );
  return (
    <div className="px-4 sm:px-6 py-6 max-w-[900px] mx-auto space-y-5">
      <PageHeader eyebrow={`Impromptu result · ${THEMES[theme].name}`} title={topic ?? ""} />
      {error && (
        <Notice tone="bad">
          {error}{" "}
          {lastTalk && (
            <button className="font-semibold underline" onClick={() => void judge(lastTalk.blob, lastTalk.seconds)}>
              Try again
            </button>
          )}
        </Notice>
      )}
      {r && (
        <>
          <Card>
            <div className="flex flex-col sm:flex-row sm:items-center gap-5">
              {r.judged ? (
                <div className="text-center sm:pr-6 sm:border-r" style={{ borderColor: "var(--line)" }}>
                  <p className="text-5xl font-semibold tabular-nums" style={{ color: "var(--ink)" }}>{Math.round(r.understanding)}</p>
                  <p className="text-xs font-semibold mt-1" style={{ color: "var(--accent-ink)" }}>{r.verdict}</p>
                </div>
              ) : null}
              <div className="flex-1 space-y-3">
                <p className="text-sm leading-relaxed" style={{ color: "var(--ink-2)" }}>{r.summary}</p>
                {r.judged && (
                  <div className="flex flex-wrap gap-x-5 gap-y-2">
                    <Dots label="Accuracy" value={r.accuracy} /><Dots label="Depth" value={r.depth} />
                    <Dots label="Coverage" value={r.coverage} /><Dots label="On topic" value={r.relevance} />
                    <Dots label="Structure" value={r.structure} />
                  </div>
                )}
              </div>
            </div>
            <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 pt-4" style={{ borderTop: "1px solid var(--line)" }}>
              {([["Talk time", formatDuration(r.duration_sec)], ["Words", r.words], ["Pace", `${r.wpm} wpm`], ["Filler words", r.fillers]] as const).map(([k, v]) => (
                <div key={k}><dt className="text-xs" style={{ color: "var(--muted)" }}>{k}</dt>
                  <dd className="text-lg font-semibold" style={{ color: "var(--ink)" }}>{v}</dd></div>
              ))}
            </dl>
          </Card>
          {r.judged && (
            <div className="grid sm:grid-cols-2 gap-5">
              {list("What you clearly understood", r.understood)}
              {list("Worth adding next time", r.missed)}
              {list("Facts to double-check", r.mistakes)}
              {list("A strong 2-minute talk would cover", r.outline)}
            </div>
          )}
          {transcript && (
            <details className="text-sm" style={{ color: "var(--ink-2)" }}>
              <summary className="cursor-pointer font-semibold" style={{ color: "var(--ink)" }}>What we heard</summary>
              <p className="mt-2 leading-relaxed">{transcript}</p>
            </details>
          )}
        </>
      )}
      <div className="flex flex-col sm:flex-row gap-3">
        <Button onClick={() => reset(false)}>Spin a new topic</Button>
        <Button variant="secondary" onClick={() => reset(true)}>Try this topic again</Button>
      </div>
    </div>
  );
}
