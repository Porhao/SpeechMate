"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Loader2, Send } from "lucide-react";
import { presentationService } from "@/services/presentation";
import type { CoachChatMessage } from "@/types";
import { cn } from "@/lib/utils";

const STARTERS = [
  "What should I fix first?",
  "How do I improve my pacing?",
  "Give me a better opening line.",
  "Am I improving compared to my earlier attempts?",
];

/** Follow-up chat with the Coach Agent about one practice run. Render with key={practiceId} so switching runs resets it. */
export default function CoachChat({ sessionId, practiceId, compact = false }: {
  sessionId: string; practiceId: string; compact?: boolean;
}) {
  const [messages, setMessages] = useState<CoachChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    presentationService.chatHistory(sessionId, practiceId)
      .then((m) => { if (!cancelled) setMessages(m); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [sessionId, practiceId]);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || loading) return;
    setMessages((m) => [...m, { role: "user", content: message, created_at: new Date().toISOString() }]);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const reply = await presentationService.chat(sessionId, practiceId, message);
      setMessages((m) => [...m, reply]);
    } catch (e) {
      setMessages((m) => m.slice(0, -1));
      setInput(message);
      setError(e instanceof Error ? e.message : "Couldn't reach the coach.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-0 h-full">
      <div ref={scroller} className={cn("flex-1 overflow-y-auto space-y-3 pr-1", compact && "max-h-[360px]")}>
        {messages.length === 0 && !loading && (
          <div className="flex flex-wrap gap-2">
            {STARTERS.map((q) => (
              <button key={q} onClick={() => send(q)} className="text-xs px-3 py-1.5 rounded-lg"
                style={{ background: "#23345C10", color: "#23345C", border: "1px solid #23345C25" }}>
                {q}
              </button>
            ))}
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={cn("flex gap-2", msg.role === "user" ? "justify-end" : "justify-start")}>
            {msg.role === "assistant" && (
              <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: "#23345C" }}>
                <Bot className="w-3.5 h-3.5 text-white" />
              </div>
            )}
            <div
              className="px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap max-w-[85%]"
              style={msg.role === "assistant"
                ? { background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#24252B", borderRadius: "14px 14px 14px 4px" }
                : { background: "#23345C", color: "white", borderRadius: "14px 14px 4px 14px" }}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && <Loader2 className="w-4 h-4 animate-spin" style={{ color: "#23345C" }} />}
      </div>

      {error && <p className="text-xs mt-2" style={{ color: "#8C3B32" }}>{error}</p>}

      <div className="flex gap-2 mt-3 flex-shrink-0">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); send(); } }}
          disabled={loading}
          maxLength={4000}
          placeholder="Ask the coach about this attempt…"
          className="flex-1 px-3 py-2 rounded-xl text-sm outline-none placeholder:text-slate-400 disabled:opacity-60"
          style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#17181C" }}
        />
        <button onClick={() => send()} disabled={loading || !input.trim()} aria-label="Send"
          className="w-9 h-9 flex items-center justify-center rounded-xl text-white disabled:opacity-40" style={{ background: "#23345C" }}>
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
