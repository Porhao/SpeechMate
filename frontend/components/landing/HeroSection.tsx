"use client";

import Link from "next/link";
import { ArrowRight, Play, Sparkles } from "lucide-react";

export default function HeroSection() {
  return (
    <section className="pt-[120px] pb-20 px-6 bg-white overflow-hidden relative">
      {/* Subtle background gradient */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(35,52,92,0.06),transparent)] pointer-events-none" />

      <div className="max-w-[1280px] mx-auto relative">
        {/* Eyebrow */}
        <div className="flex justify-center mb-5">
          <span className="inline-flex items-center gap-1.5 text-xs font-medium tracking-wide text-[#6E6C63]">
            <Sparkles className="w-3.5 h-3.5 text-[#23345C]" />
            AI-Powered Communication Training
          </span>
        </div>

        {/* Headline */}
        <div className="text-center max-w-[760px] mx-auto">
          <h1 className="font-display text-[48px] leading-[1.12] text-[#17181C] tracking-tight mb-5">
            Improve your communication
            <span className="text-[#23345C]"> with AI</span>
          </h1>
          <p className="text-[18px] text-[#6E6C63] leading-relaxed mb-8 max-w-[560px] mx-auto">
            Practice speaking, improve fluency, and build confidence through
            personalized AI coaching — anytime, anywhere.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/register"
              className="flex items-center gap-2 h-12 px-6 bg-[#23345C] text-white font-semibold rounded-[8px] hover:bg-[#17233E] transition-colors duration-200"
            >
              Start for free
              <ArrowRight className="w-4 h-4" />
            </Link>
            <button className="flex items-center gap-2 h-12 px-6 bg-white border border-[#E6E2D8] text-[#17181C] font-medium rounded-[8px] hover:bg-[#F5F2EB] transition-colors">
              <Play className="w-3.5 h-3.5 text-[#23345C] fill-[#23345C]" />
              Watch demo
            </button>
          </div>

          <p className="mt-4 text-xs text-[#9B988E]">No credit card required · Supports English & Bahasa Melayu</p>
        </div>

        {/* Hero Visual — App Preview Card */}
        <div className="mt-16 max-w-[900px] mx-auto">
          <div className="bg-white rounded-2xl border border-[#E6E2D8] shadow-[0px_20px_60px_rgba(0,0,0,0.08)] overflow-hidden">
            {/* Fake browser chrome */}
            <div className="bg-[#F5F2EB] border-b border-[#E6E2D8] px-4 py-3 flex items-center gap-2">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-[#9C4A40]" />
                <div className="w-3 h-3 rounded-full bg-[#9C6A28]" />
                <div className="w-3 h-3 rounded-full bg-[#4D7A59]" />
              </div>
              <div className="flex-1 mx-4 bg-white border border-[#E6E2D8] rounded-md h-6 flex items-center px-3">
                <span className="text-xs text-[#9B988E]">app.speechmate.ai/session</span>
              </div>
            </div>

            {/* App preview */}
            <div className="grid grid-cols-[1fr_1.8fr_1.2fr] divide-x divide-[#E6E2D8] h-[360px]">
              {/* Video column */}
              <div className="bg-[#17181C] flex items-center justify-center flex-col gap-3 p-4">
                <div className="w-16 h-16 rounded-full bg-[#23345C]/20 border-2 border-[#23345C]/40 flex items-center justify-center">
                  <div className="w-8 h-8 rounded-full bg-[#23345C] flex items-center justify-center">
                    <span className="text-white text-xs font-bold">SM</span>
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-white text-xs font-medium">Live Session</div>
                  <div className="flex items-center gap-1 justify-center mt-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#4D7A59] animate-pulse" />
                    <span className="text-[#4D7A59] text-[10px]">Recording</span>
                  </div>
                </div>
                {/* Audio waveform */}
                <div className="flex items-center gap-0.5 mt-2">
                  {[3, 6, 10, 7, 4, 8, 12, 6, 3, 9, 5].map((h, i) => (
                    <div
                      key={i}
                      className="w-1 bg-[#23345C] rounded-full opacity-80"
                      style={{ height: `${h}px` }}
                    />
                  ))}
                </div>
              </div>

              {/* Conversation column */}
              <div className="flex flex-col p-4 gap-3 overflow-hidden">
                <div className="text-xs font-semibold text-[#6E6C63] uppercase tracking-wide">Conversation</div>
                {/* AI message */}
                <div className="flex gap-2">
                  <div className="w-6 h-6 rounded-full bg-[#5A5470] flex items-center justify-center shrink-0 mt-0.5">
                    <span className="text-white text-[9px] font-bold">AI</span>
                  </div>
                  <div className="bg-[#F5F2EB] rounded-xl rounded-tl-sm px-3 py-2 text-sm text-[#17181C] max-w-[85%]">
                    Tell me about a time you faced a challenge at work.
                  </div>
                </div>
                {/* User message */}
                <div className="flex justify-end">
                  <div className="bg-[#23345C] rounded-xl rounded-tr-sm px-3 py-2 text-sm text-white max-w-[85%]">
                    I once had to present to a large team on very short notice...
                  </div>
                </div>
                {/* AI message */}
                <div className="flex gap-2">
                  <div className="w-6 h-6 rounded-full bg-[#5A5470] flex items-center justify-center shrink-0 mt-0.5">
                    <span className="text-white text-[9px] font-bold">AI</span>
                  </div>
                  <div className="bg-[#F5F2EB] rounded-xl rounded-tl-sm px-3 py-2 text-sm text-[#17181C] max-w-[85%]">
                    Good structure! Try to slow down slightly — your pace is excellent.
                  </div>
                </div>
                {/* Typing indicator */}
                <div className="flex gap-1.5 items-center pl-8">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#9B988E] animate-bounce" style={{ animationDelay: "0ms" }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-[#9B988E] animate-bounce" style={{ animationDelay: "150ms" }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-[#9B988E] animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>

              {/* Feedback column */}
              <div className="p-4 flex flex-col gap-3">
                <div className="text-xs font-semibold text-[#6E6C63] uppercase tracking-wide">Live Feedback</div>
                {[
                  { label: "Fluency", score: 82, color: "#4D7A59" },
                  { label: "Pronunciation", score: 74, color: "#23345C" },
                  { label: "Eye Contact", score: 68, color: "#5A5470" },
                  { label: "Confidence", score: 79, color: "#9C6A28" },
                  { label: "Speaking Pace", score: 91, color: "#4D7A59" },
                ].map((m) => (
                  <div key={m.label}>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[11px] text-[#6E6C63]">{m.label}</span>
                      <span className="text-[11px] font-semibold text-[#17181C]">{m.score}%</span>
                    </div>
                    <div className="h-1.5 bg-[#F1EEE6] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${m.score}%`, backgroundColor: m.color }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-12 flex flex-wrap justify-center gap-8">
          {[
            { value: "10,000+", label: "Practice sessions" },
            { value: "94%", label: "Users improved fluency" },
            { value: "5 min", label: "To see first results" },
            { value: "2", label: "Languages supported" },
          ].map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-2xl font-bold text-[#17181C]">{s.value}</div>
              <div className="text-sm text-[#6E6C63] mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
