"use client";

// Home: the three things SpeechMate does, how each works in three steps, and
// where you are (real stats, your latest focus, recent sessions).

import Link from "next/link";
import { ArrowRight, Briefcase, ChevronRight, MessageCircle, Presentation } from "lucide-react";
import { useUserStore } from "@/store/useUserStore";
import { useMyStats } from "@/hooks/useMyStats";
import { Card } from "@/components/ui/kit";
import type { LiveSession } from "@/types";

const FUNCTIONS = [
  {
    href: "/conversation", icon: MessageCircle, color: "#23345C", kicker: "Everyday speaking",
    title: "Daily conversation",
    desc: "Chat naturally with an AI partner about everyday topics.",
    steps: ["Pick a topic", "Talk for 3–5 minutes", "Get your voice, language, body-language and confidence report"],
    cta: "Start a conversation",
  },
  {
    href: "/interview", icon: Briefcase, color: "#5A5470", kicker: "Job ready",
    title: "Mock interview",
    desc: "A realistic interview with questions curated for your role and resume.",
    steps: ["Enter the position and your background (+ resume)", "Answer the interviewer's questions", "Get feedback on every answer, with a stronger version"],
    cta: "Set up an interview",
  },
  {
    href: "/presentations", icon: Presentation, color: "#8A5A22", kicker: "Slides & Q&A",
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
    <div className="px-4 sm:px-6 py-8 sm:py-10 max-w-[1200px] mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-3xl sm:text-4xl leading-tight" style={{ color: "var(--ink)" }}>
          {firstName ? `Hello, ${firstName}.` : "Hello."} What would you like to practise?
        </h1>
        <p className="mt-2 text-[15px]" style={{ color: "var(--ink-2)" }}>
          Speak with the AI, then get a clear, simple report. Nothing interrupts you while you talk.
        </p>
      </div>

      {/* The three functions */}
      <div className="grid md:grid-cols-3 gap-4 mb-8">
        {FUNCTIONS.map(({ href, icon: Icon, color, kicker, title, desc, steps, cta }) => (
          <Link key={href} href={href} className="group flex flex-col transition-transform hover:-translate-y-0.5"
            style={{ background: "var(--surface)", border: "1px solid var(--line)" }}>
            <div className="p-5 text-white" style={{ background: color }}>
              <Icon className="w-6 h-6 text-white/85" strokeWidth={1.6} />
              <p className="text-[11px] uppercase tracking-wide text-white/60 mt-4">{kicker}</p>
              <h2 className="font-display text-2xl leading-tight">{title}</h2>
              <p className="text-sm text-white/75 mt-1.5 leading-relaxed">{desc}</p>
            </div>
            <ol className="p-5 space-y-2.5 flex-1">
              {steps.map((s, i) => (
                <li key={s} className="flex gap-3 text-sm" style={{ color: "var(--ink-2)" }}>
                  <span className="w-5 h-5 flex-shrink-0 flex items-center justify-center text-[11px] font-bold" style={{ background: "var(--surface-2)", color: "var(--ink)" }}>{i + 1}</span>
                  {s}
                </li>
              ))}
            </ol>
            <span className="mx-5 mb-5 pt-3 flex items-center justify-between text-sm font-semibold" style={{ borderTop: "1px solid var(--line-2)", color: "var(--accent-ink)" }}>
              {cta} <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>
        ))}
      </div>

      {/* Where you are */}
      <div className="grid lg:grid-cols-[1fr_1fr] gap-4">
        <Card title="Your next focus">
          {focus ? (
            <>
              <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>{focus.title}</p>
              {focus.evidence && <p className="text-sm mt-1" style={{ color: "var(--ink-2)" }}>{focus.evidence}</p>}
              <p className="text-sm mt-3 p-3" style={{ background: "var(--surface-2)", color: "var(--ink-3)" }}>
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
            <ul className="divide-y" style={{ borderColor: "var(--line-2)" }}>
              {stats.recent.slice(0, 4).map((s) => (
                <li key={s.id}>
                  <Link href={`/results/${s.id}`} className="flex items-center gap-3 py-2.5">
                    <span className="w-9 font-display text-lg tabular-nums" style={{ color: score(s) != null ? "var(--ink)" : "var(--faint)" }}>{score(s) ?? "—"}</span>
                    <span className="flex-1 text-sm truncate" style={{ color: "var(--ink-2)" }}>{TYPE_LABEL[s.session_type] ?? s.session_type}</span>
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
