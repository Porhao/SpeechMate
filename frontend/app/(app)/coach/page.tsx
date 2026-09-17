"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, Loader2, RotateCcw, Sparkles } from "lucide-react";
import { coachService } from "@/services/coach";
import type { ChatMessage } from "@/types";
import { cn } from "@/lib/utils";

const SUGGESTIONS = [
  {
    category: "Fluency",
    color: "#23345C",
    questions: [
      "Why is my fluency score not improving?",
      "How can I reduce filler words like 'um' and 'uh'?",
      "What exercises help with speaking pace?",
    ],
  },
  {
    category: "Pronunciation",
    color: "#5A5470",
    questions: [
      "How do I improve my pronunciation of difficult English phonemes?",
      "What are common Malaysian English accent patterns I should be aware of?",
      "How can I practice BM-English code-switching more naturally?",
    ],
  },
  {
    category: "Confidence",
    color: "#8A5A22",
    questions: [
      "How do I become more confident when presenting?",
      "What techniques help with presentation anxiety?",
      "How can I project more authority in my voice?",
    ],
  },
  {
    category: "Eye Contact",
    color: "#3F6B4C",
    questions: [
      "How do I maintain better eye contact during presentations?",
      "My eye contact score keeps dropping — what should I do?",
      "Tips for looking natural on camera?",
    ],
  },
];

// Timestamp is intentionally blank here — `new Date()` at module scope would
// be evaluated once during SSR and again on the client at a different wall
// clock time, causing a hydration mismatch. The real timestamp is filled in
// client-side after mount instead (see the effect in CoachPage below).
const SYSTEM_GREETING: ChatMessage = {
  role: "assistant",
  content:
    "Hello! I'm your SpeechMate AI Coach. I'm here to help you improve your communication skills — whether it's fluency, pronunciation, eye contact, confidence, or presentation techniques.\n\nI have access to your practice history and can give you personalized advice. What would you like to work on today?",
  timestamp: "",
};

function formatTime(iso: string) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("en-MY", { hour: "2-digit", minute: "2-digit" });
}

export default function CoachPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([SYSTEM_GREETING]);
  const [input,    setInput]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Stamp the greeting with a real time once we're on the client.
  useEffect(() => {
    setMessages((prev) =>
      prev.length === 1 && prev[0].timestamp === ""
        ? [{ ...prev[0], timestamp: new Date().toISOString() }]
        : prev,
    );
  }, []);

  const sendMessage = async (text?: string) => {
    const question = (text ?? input).trim();
    if (!question || loading) return;

    const userMsg: ChatMessage = { role: "user", content: question, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const history = [...messages, userMsg];
      const res = await coachService.chat(question, history);
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer, timestamp: new Date().toISOString() }]);
    } catch {
      setError("Couldn't reach the AI coach. Please try again.");
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const resetChat = () => {
    setMessages([{ ...SYSTEM_GREETING, timestamp: new Date().toISOString() }]);
    setInput("");
    setError(null);
  };

  const allQuestions = SUGGESTIONS.flatMap((s) => s.questions.map((q) => ({ q, color: s.color })));

  return (
    <div className="flex flex-col lg:flex-row px-3 sm:px-6 py-3 sm:py-4 max-w-[1320px] mx-auto gap-4 lg:gap-5" style={{ height: "calc(100dvh - 60px)" }}>

      {/* Sidebar: Suggested questions — full panel on large screens */}
      <div className="hidden lg:block w-[268px] flex-shrink-0 overflow-y-auto">
        <div className="space-y-3 pb-4">
          <div className="flex items-center gap-2 py-1">
            <Sparkles className="w-4 h-4" style={{ color: "#23345C" }} />
            <p className="text-sm font-semibold" style={{ color: "#17181C" }}>Suggested questions</p>
          </div>

          {SUGGESTIONS.map(({ category, color, questions }) => (
            <div key={category} className="glass-card rounded-2xl p-4">
              <div className="mb-3">
                <span
                  className="text-[10px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wide"
                  style={{ backgroundColor: `${color}18`, color }}
                >
                  {category}
                </span>
              </div>
              <div className="space-y-2">
                {questions.map((q) => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    disabled={loading}
                    className="w-full text-left text-xs px-2 py-1.5 rounded-lg transition-colors disabled:opacity-50 leading-relaxed"
                    style={{ color: "#6E6C63" }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "#F1EEE6"; e.currentTarget.style.color = "#17181C"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#6E6C63"; }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ))}

          <div
            className="rounded-xl px-4 py-3"
            style={{ background: "rgba(35,52,92,0.06)", border: "1px solid rgba(35,52,92,0.16)" }}
          >
            <p className="text-[10px] leading-relaxed" style={{ color: "#6E6C63" }}>
              The AI coach has access to your practice history, scores, and progress data to give you personalized advice.
            </p>
          </div>
        </div>
      </div>

      {/* Suggested questions — compact horizontal scroller below lg */}
      <div className="lg:hidden flex-shrink-0 -mx-3 sm:-mx-6 px-3 sm:px-6">
        <div className="flex items-center gap-1.5 mb-2">
          <Sparkles className="w-3.5 h-3.5" style={{ color: "#23345C" }} />
          <p className="text-xs font-semibold" style={{ color: "#17181C" }}>Suggested</p>
        </div>
        <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
          {allQuestions.map(({ q, color }) => (
            <button
              key={q}
              onClick={() => sendMessage(q)}
              disabled={loading}
              className="flex-shrink-0 text-left text-xs px-3 py-2 rounded-xl whitespace-nowrap transition-colors disabled:opacity-50"
              style={{ background: `${color}10`, color, border: `1px solid ${color}25`, maxWidth: 260 }}
            >
              <span className="block truncate">{q}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Header */}
        <div className="flex items-center justify-between py-3 px-1 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: "#23345C" }}>
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold" style={{ color: "#17181C" }}>SpeechMate AI Coach</p>
              <p className="text-xs flex items-center gap-1" style={{ color: "#3F6B4C" }}>
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                Online · Powered by GPT-4o
              </p>
            </div>
          </div>
          <button
            onClick={resetChat}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-xl transition-colors"
            style={{ color: "#6E6C63", border: "1px solid #E6E2D8", background: "#F5F2EB" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "#17181C"; e.currentTarget.style.background = "#F1EEE6"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "#6E6C63"; e.currentTarget.style.background = "#F5F2EB"; }}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            New chat
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto glass-card rounded-2xl p-5 mb-3">
          <div className="space-y-5 max-w-[860px]">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={cn("flex gap-3", msg.role === "user" ? "justify-end" : "justify-start")}
              >
                {msg.role === "assistant" && (
                  <div
                    className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
                    style={{ background: "#23345C" }}
                  >
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}

                <div className={cn("flex flex-col gap-1", msg.role === "user" ? "items-end max-w-[70%]" : "items-start max-w-[80%]")}>
                  <div
                    className="px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap"
                    style={msg.role === "assistant"
                      ? {
                          background: "#F5F2EB",
                          border: "1px solid #E6E2D8",
                          color: "#24252B",
                          borderRadius: "16px 16px 16px 4px",
                        }
                      : {
                          background: "#23345C",
                          color: "white",
                          borderRadius: "16px 16px 4px 16px",
                        }
                    }
                  >
                    {msg.content}
                  </div>
                  <span className="text-[10px] px-1" style={{ color: "#CDC9BE" }}>
                    {formatTime(msg.timestamp)}
                  </span>
                </div>

                {msg.role === "user" && (
                  <div
                    className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
                    style={{ background: "rgba(35,52,92,0.14)", border: "1px solid rgba(35,52,92,0.3)" }}
                  >
                    <span className="text-xs font-bold" style={{ color: "#17233E" }}>Me</span>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-3">
                <div
                  className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: "#23345C" }}
                >
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div
                  className="px-4 py-3 rounded-2xl"
                  style={{ background: "#F5F2EB", border: "1px solid #E6E2D8" }}
                >
                  <div className="flex items-center gap-1">
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="w-1.5 h-1.5 rounded-full animate-bounce"
                        style={{ background: "#93C5FD", animationDelay: `${i * 0.15}s` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div
                className="flex items-center gap-2 text-sm px-4 py-3 rounded-xl"
                style={{ background: "rgba(140,59,50,0.06)", border: "1px solid rgba(140,59,50,0.25)", color: "#8C3B32" }}
              >
                {error}
                <button onClick={() => setError(null)} className="ml-auto text-xs underline">Dismiss</button>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <div
          className="rounded-2xl p-3 flex gap-3 flex-shrink-0"
          style={{ background: "#FFFFFF", border: "1px solid #E6E2D8", boxShadow: "var(--shadow-card)" }}
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            disabled={loading}
            placeholder="Ask your AI coach anything about your communication skills..."
            className="flex-1 px-4 py-2.5 rounded-xl text-sm outline-none transition-all disabled:opacity-60 placeholder:text-slate-400"
            style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#17181C" }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(35,52,92,0.5)"; }}
            onBlur={(e) => { e.currentTarget.style.borderColor = "#E6E2D8"; }}
          />
          <button
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
            className="w-10 h-10 flex items-center justify-center rounded-xl text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
            style={{ background: "#23345C" }}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
