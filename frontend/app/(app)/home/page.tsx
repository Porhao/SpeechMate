"use client";

// Home: the three things SpeechMate does, how each works in three steps, and
// where you are (real stats, your latest focus, recent sessions).

import Link from "next/link";
import { ArrowRight, Briefcase, ChevronRight, MessageCircle, Presentation } from "lucide-react";
import { useUserStore } from "@/store/useUserStore";
import { useMyStats } from "@/hooks/useMyStats";
import { Card, TiltCard } from "@/components/ui/kit";
import ClayArt from "@/components/three/ClayArt";
import type { LiveSession } from "@/types";

const FUNCTIONS = [
  {
    href: "/conversation", icon: MessageCircle, bg: "var(--pink)", fg: "#fff", kicker: "Everyday speaking",
    title: "Daily conversation",
    desc: "Chat naturally with an AI partner about everyday topics.",
    steps: ["Pick a topic", "Talk for 3–5 minutes", "Get your voice, language, body-language and confidence report"],
    cta: "Start a conversation",
  },
  {
    href: "/interview", icon: Briefcase, bg: "var(--teal)", fg: "#fff", kicker: "Job ready",
    title: "Mock interview",
    desc: "A realistic interview with questions curated for your role and resume.",
    steps: ["Enter the position and your background (+ resume)", "Answer the interviewer's questions", "Get feedback on every answer, with a stronger version"],
    cta: "Set up an interview",
  },
  {
    href: "/presentations", icon: Presentation, bg: "var(--lavender)", fg: "#0A0A0A", kicker: "Slides & Q&A",
    title: "Presentation practice",
    desc: "Upload your deck; the AI studies it, coaches your delivery and runs your Q&A.",
    steps: ["Upload .pptx or .pdf: get a summary and insights", "Rehearse the talk, slide by slide", "Answer audience questions drawn from your deck"],
    cta: "Upload a deck",
  },
] as const;

const TYPE_LABEL: Record<string, string> = { Conversation: "Conversation", Interview: "Mock interview", Presentation: "Presentation Q&A", Pronunciation: "Pronunciation" };

function score(s: LiveSession) {
  const v = s.analysis?.communication_score.overall_score;
  return v != null ? Math.round(v) : null;
}

export default function HomePage() {
  const { user } = useUserStore();
  const { stats, signedIn } = useMyStats();
  const firstName = user?.full_name?.split(" ")[0];
  const latestDone = stats?.recent.find((s) => s.status === "complete" && s.analysis);
  const focus = latestDone?.analysis?.recommendations.exercises[0];

  return (
    <div className="px-4 sm:px-6 py-8 sm:py-12 max-w-[1280px] mx-auto">
      {/* Hero: headline left, 3D orb right (7/5) */}
      <div className="grid lg:grid-cols-[7fr_5fr] items-center gap-6 mb-10 lg:mb-14">
        <div>
          <p className="inline-block text-[13px] font-medium px-3 py-1 rounded-full mb-5" style={{ background: "var(--surface-3)", color: "var(--ink-2)" }}>
            {firstName ? `Hello, ${firstName}` : "Welcome back"}
          </p>
          <h1 className="font-display text-[40px] sm:text-[56px] lg:text-[64px] leading-[1.02]" style={{ color: "var(--ink)" }}>
            What would you like to practise today?
          </h1>
          <p className="mt-5 text-base sm:text-lg max-w-xl" style={{ color: "var(--ink-2)" }}>
            Speak with the AI, then get a clear, simple report. Nothing interrupts you while you talk.
          </p>
        </div>
        {/* 3D clay microphone, speech bubbles and shapes (click to squash) */}
        <ClayArt variant="mic" className="h-[360px]" />
      </div>

      {/* The three functions: saturated clay cards that lean towards the pointer */}
      <div className="grid md:grid-cols-3 gap-5 mb-10">
        {FUNCTIONS.map(({ href, icon: Icon, bg, fg, kicker, title, desc, steps, cta }) => (
          <TiltCard key={href} href={href} className="group flex flex-col rounded-xl p-6 sm:p-7" style={{ background: bg, color: fg }}>
            <span className="tilt-pop w-12 h-12 rounded-lg flex items-center justify-center clay" style={{ background: "rgba(255,255,255,0.22)" }}>
              <Icon className="w-6 h-6" strokeWidth={1.8} />
            </span>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] mt-6 opacity-75">{kicker}</p>
            <h2 className="font-display text-[28px] leading-tight mt-1">{title}</h2>
            <p className="text-sm mt-2 leading-relaxed opacity-85">{desc}</p>
            {/* Product fragment: the three steps on a small white panel */}
            <ol className="tilt-pop mt-6 p-4 rounded-lg space-y-2.5 flex-1" style={{ background: "#FFFAF0", color: "#3A3A3A" }}>
              {steps.map((s, i) => (
                <li key={s} className="flex gap-3 text-sm">
                  <span className="w-5 h-5 flex-shrink-0 rounded-full flex items-center justify-center text-[11px] font-bold" style={{ background: bg, color: fg }}>{i + 1}</span>
                  {s}
                </li>
              ))}
            </ol>
            <span className="mt-5 flex items-center justify-between text-sm font-semibold">
              {cta} <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </span>
          </TiltCard>
        ))}
      </div>

      {/* Where you are */}
      <div className="grid lg:grid-cols-2 gap-5">
        <Card title="Your next focus">
          {focus ? (
            <>
              <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>{focus.title}</p>
              {focus.evidence && <p className="text-sm mt-1" style={{ color: "var(--ink-2)" }}>{focus.evidence}</p>}
              <p className="text-sm mt-3 p-3 rounded-md" style={{ background: "var(--surface-3)", color: "var(--ink-3)" }}>
                <b>Try:</b> {focus.description}
              </p>
              <Link href={`/results/${latestDone!.id}`} className="inline-flex items-center gap-1 text-xs font-semibold mt-3" style={{ color: "var(--accent-ink)" }}>
                From your last session <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </>
          ) : (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              {signedIn ? "Finish a session and your most useful next step appears here." : "Sign in to get a personal next step after each session."}
            </p>
          )}
        </Card>

        <Card title="Recent sessions" action={stats && stats.sessions > 0 && (
          <Link href="/progress" className="text-xs font-semibold" style={{ color: "var(--accent-ink)" }}>See progress</Link>
        )}>
          {stats && stats.recent.length > 0 ? (
            <ul className="divide-y divide-[var(--line-2)]">
              {stats.recent.slice(0, 4).map((s) => (
                <li key={s.id}>
                  <Link href={`/results/${s.id}`} className="flex items-center gap-3 py-2.5">
                    <span className="w-9 font-display text-lg tabular-nums" style={{ color: score(s) != null ? "var(--ink)" : "var(--faint)" }}>{score(s) ?? "—"}</span>
                    <span className="flex-1 text-sm truncate" style={{ color: "var(--ink-2)" }}>{s.context?.kind === "talk" ? "Presentation" : TYPE_LABEL[s.session_type] ?? s.session_type}</span>
                    <span className="text-xs" style={{ color: "var(--muted)" }}>{new Date(s.created_at).toLocaleDateString("en-MY", { day: "numeric", month: "short" })}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm" style={{ color: "var(--muted)" }}>{stats ? "No sessions yet." : signedIn ? "Loading…" : "Sign in to see your sessions."}</p>
          )}
          {stats && stats.sessions > 0 && (
            <p className="text-xs mt-3" style={{ color: "var(--muted)" }}>
              {stats.sessions} session{stats.sessions === 1 ? "" : "s"} · {stats.practiceMinutes} min practised
              {stats.streakDays > 1 ? ` · ${stats.streakDays}-day streak` : ""}
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}
