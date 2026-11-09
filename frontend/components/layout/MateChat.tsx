"use client";

// Mate's chat box: opens from the companion in the corner. Ask how the app works, what your
// results mean, or for speaking advice (backend services/assistant.py; Gemini, with your profile
// and recent sessions). The conversation lives only in this tab (sessionStorage); nothing is
// saved on the server. Page paths in a reply (/progress, …) become links.

import { Fragment, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Send, X } from "lucide-react";
import { api } from "@/services/api";

type Msg = { role: "user" | "assistant"; text: string };

const KEY = "speechmate:mate-chat";
const SUGGESTIONS = [
  "How did my last session go?",
  "What should I practise next?",
  "How do I prepare for a presentation?",
  "What does the confidence score mean?",
];
const PAGE = /(\/(?:home|conversation|interview|presentations|script|progress|profile|settings|privacy|methodology|results\/[\w-]+))\b/g;

const load = (): Msg[] => { try { return JSON.parse(sessionStorage.getItem(KEY) ?? "[]"); } catch { return []; } };
const save = (m: Msg[]) => { try { sessionStorage.setItem(KEY, JSON.stringify(m.slice(-40))); } catch { /* private mode */ } };

/** A reply's text with the app's page paths turned into links. */
function Linked({ text, onNavigate }: { text: string; onNavigate: () => void }) {
  return <>{text.split(PAGE).map((part, i) => i % 2
    ? <Link key={i} href={part} onClick={onNavigate} className="underline font-semibold" style={{ color: "var(--accent-ink)" }}>{part}</Link>
    : <Fragment key={i}>{part}</Fragment>)}</>;
}

export default function MateChat({ onClose, onThinking }: { onClose: () => void; onThinking: (busy: boolean) => void }) {
  const pathname = usePathname();
  const [msgs, setMsgs] = useState<Msg[]>(load);
  const [draft, setDraft] = useState("");
  const [waiting, setWaiting] = useState(false);
  const list = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { input.current?.focus(); }, []);
  useEffect(() => { list.current?.scrollTo({ top: list.current.scrollHeight, behavior: "smooth" }); save(msgs); }, [msgs, waiting]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const send = async (text: string) => {
    const t = text.trim();
    if (!t || waiting) return;
    const next = [...msgs, { role: "user" as const, text: t }];
    setMsgs(next); setDraft(""); setWaiting(true); onThinking(true);
    try {
      const { reply } = await api.post<{ reply: string }>("/assistant/chat", { messages: next.slice(-12), page: pathname });
      setMsgs((m) => [...m, { role: "assistant", text: reply }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "assistant", text: e instanceof Error ? `Sorry, I couldn't answer that: ${e.message}` : "Sorry, something went wrong." }]);
    } finally { setWaiting(false); onThinking(false); }
  };

  return (
    <section role="dialog" aria-label="Chat with Mate" className="mascot-bubble pointer-events-auto flex flex-col rounded-2xl overflow-hidden"
      style={{ width: "min(360px, calc(100vw - 32px))", height: "min(480px, 70vh)", background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow-card)" }}>
      <header className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: "1px solid var(--line)" }}>
        <span className="flex-1">
          <span className="block text-sm font-semibold" style={{ color: "var(--ink)" }}>Mate</span>
          <span className="block text-[11px]" style={{ color: "var(--muted)" }}>Ask about the app, your results or speaking</span>
        </span>
        {msgs.length > 0 && (
          <button onClick={() => setMsgs([])} className="text-[11px] underline" style={{ color: "var(--muted)" }}>Clear</button>
        )}
        <button onClick={onClose} aria-label="Close chat" className="nav-pill w-8 h-8 rounded-full flex items-center justify-center"><X className="w-4 h-4" /></button>
      </header>

      <div ref={list} className="flex-1 overflow-y-auto px-3 py-3 space-y-2" aria-live="polite">
        {msgs.length === 0 && (
          <div className="space-y-2">
            <p className="text-sm px-1" style={{ color: "var(--ink-2)" }}>Hi! I&apos;m Mate. Ask me anything about SpeechMate or your speaking. For example:</p>
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)} className="nav-pill block w-full text-left text-sm px-3 py-2 rounded-xl">{s}</button>
            ))}
          </div>
        )}
        {msgs.map((m, i) => (
          <p key={i} className={`text-sm leading-relaxed whitespace-pre-line px-3 py-2 rounded-2xl max-w-[85%] ${m.role === "user" ? "ml-auto rounded-br-sm" : "rounded-bl-sm"}`}
            style={m.role === "user" ? { background: "var(--accent)", color: "#fff" } : { background: "var(--surface-2)", color: "var(--ink)" }}>
            {m.role === "assistant" ? <Linked text={m.text} onNavigate={onClose} /> : m.text}
          </p>
        ))}
        {waiting && (
          <p className="inline-flex gap-1 px-3 py-3 rounded-2xl rounded-bl-sm" style={{ background: "var(--surface-2)" }} aria-label="Mate is typing">
            {[0, 1, 2].map((i) => <span key={i} className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: "var(--muted)", animationDelay: `${i * 0.15}s` }} />)}
          </p>
        )}
      </div>

      <form className="flex items-end gap-2 p-2" style={{ borderTop: "1px solid var(--line)" }} onSubmit={(e) => { e.preventDefault(); send(draft); }}>
        <textarea ref={input} value={draft} onChange={(e) => setDraft(e.target.value)} rows={1} maxLength={2000}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(draft); } }}
          placeholder="Ask Mate…" aria-label="Message Mate"
          className="flex-1 resize-none text-sm px-3 py-2 rounded-xl outline-none max-h-28"
          style={{ background: "var(--surface-2)", color: "var(--ink)", border: "1px solid var(--line)" }} />
        <button type="submit" disabled={!draft.trim() || waiting} aria-label="Send"
          className="w-9 h-9 rounded-full flex items-center justify-center text-white disabled:opacity-40" style={{ background: "var(--accent)" }}>
          <Send className="w-4 h-4" />
        </button>
      </form>
    </section>
  );
}
