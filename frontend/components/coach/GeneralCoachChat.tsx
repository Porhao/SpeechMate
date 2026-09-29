"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Loader2, Send } from "lucide-react";
import { conversationService } from "@/services/live";
import { cn } from "@/lib/utils";

type Msg = { role: "user" | "assistant"; content: string };

const SUGGESTIONS = [
  "How can I reduce filler words like 'um' and 'uh'?",
  "What exercises help with speaking pace?",
  "What are common Malaysian English accent patterns I should be aware of?",
  "How can I practice BM-English code-switching more naturally?",
  "What techniques help with presentation anxiety?",
  "How do I maintain better eye contact during presentations?",
];

/** The general AI coach (POST /api/coach/chat). Signed-in users get advice
 *  grounded in their profile and most recent analysed live sessions. */
export default function GeneralCoachChat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text?: string) => {
    const question = (text ?? input).trim();
    if (!question || loading) return;
    const history = messages;
    setMessages([...history, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const { answer } = await conversationService.coach(question, history);
      setMessages((m) => [...m, { role: "assistant", content: answer }]);
    } catch (e) {
      setMessages(history);
      setInput(question);
      setError(e instanceof Error ? e.message : "Couldn't reach the AI coach.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-0 h-full">
      <div ref={scroller} className="flex-1 overflow-y-auto space-y-3 pr-1">
        {messages.length === 0 && (
          <>
            <p className="text-sm" style={{ color: "#4B4C52" }}>
              Ask about fluency, pronunciation, confidence, eye contact or presenting. Sign in and the coach
              also sees your goal and your latest session results.
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((q) => (
                <button key={q} onClick={() => send(q)} className="text-xs px-3 py-1.5 rounded-lg text-left"
                  style={{ background: "#23345C10", color: "#23345C", border: "1px solid #23345C25" }}>
                  {q}
                </button>
              ))}
            </div>
          </>
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
          placeholder="Ask your AI coach anything about your communication skills…"
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
