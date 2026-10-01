"use client";

import { useRouter } from "next/navigation";
import { useMyStats } from "@/hooks/useMyStats";
import {
  MessageCircle,
  Briefcase,
  Presentation,
  Volume2,
  Clock,
  Star,
  ChevronRight,
  Play,
  Zap,
  Target,
  TrendingUp,
} from "lucide-react";
import { tint, inkOf } from "@/lib/utils";

const MODES = [
  {
    id: "Conversation",
    title: "AI Conversation",
    description: "Practice natural conversations on everyday topics. The AI will engage you in flowing dialogue, prompting follow-up questions to build your spontaneous speaking confidence.",
    icon: MessageCircle,
    color: "#23345C",
    dark: "#17233E",
    level: "All Levels",
    levelColor: "#3F6B4C",
    duration: "10–30 min",
    tags: ["Fluency", "Confidence", "Spontaneity"],
  },
  {
    id: "Interview",
    title: "Mock Interview",
    description: "Simulate job interviews, university admissions, and scholarship panels. Receive feedback on your answers, tone, eye contact, and overall professionalism.",
    icon: Briefcase,
    color: "#5A5470",
    dark: "#48435C",
    level: "Intermediate+",
    levelColor: "#8A5A22",
    duration: "15–45 min",
    tags: ["Professional", "Eye Contact", "Structure"],
  },
  {
    id: "Presentation",
    title: "Presentation Practice",
    description: "Upload your slides and get an AI-narrated example presentation in your own voice. Then practise it and get Observation → Impact → Suggestion coaching plus a simulated audience's reaction.",
    icon: Presentation,
    color: "#8A5A22",
    dark: "#6B4419",
    level: "Advanced",
    levelColor: "#8C3B32",
    duration: "5–60 min",
    tags: ["Posture", "Pace", "Structure"],
  },
  {
    id: "Pronunciation",
    title: "Pronunciation Training",
    description: "Targeted drills for English phonemes, BM sounds, and code-switching patterns. Word-level accuracy scoring with instant phoneme feedback.",
    icon: Volume2,
    color: "#3F6B4C",
    dark: "#2E4F38",
    level: "All Levels",
    levelColor: "#3F6B4C",
    duration: "5–20 min",
    tags: ["Phonemes", "BM English", "Accuracy"],
  },
];


function gradeColor(score: number) {
  if (score >= 90) return "#3F6B4C";
  if (score >= 80) return "#23345C";
  if (score >= 70) return "#8A5A22";
  return "#8C3B32";
}

export default function PracticePage() {
  const router = useRouter();
  const { stats, signedIn } = useMyStats();
  // Presentation practice runs on the backend's upload → ideal video → coach flow.
  const startSession = (mode: string) =>
    router.push(mode === "Presentation" ? "/presentations" : `/session?mode=${encodeURIComponent(mode)}`);

  return (
    <div className="px-4 sm:px-6 py-6 sm:py-8 max-w-[1320px] mx-auto space-y-8">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl" style={{ color: "var(--ink)" }}>Practice Center</h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            Choose a mode and start improving your communication skills
          </p>
        </div>
        <div
          className="flex items-center gap-2 text-sm px-4 py-2 rounded-xl"
          style={{ background: "var(--surface-2)", border: "1px solid var(--line)", color: "var(--ink-2)" }}
        >
          <Target className="w-4 h-4" style={{ color: "var(--accent-ink)" }} />
          This week:
          <span className="font-semibold ml-1" style={{ color: "var(--ink)" }}>
            {stats ? `${stats.thisWeek} session${stats.thisWeek === 1 ? "" : "s"}` : "—"}
          </span>
        </div>
      </div>

      {/* Mode Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {MODES.map((mode, i) => (
          <div
            key={mode.id}
            className="glass-card rounded-2xl p-6 flex flex-col transition-all cursor-default slide-up"
            style={{ transition: "box-shadow 0.2s ease, transform 0.2s ease", animationDelay: `${i * 0.07}s` }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLDivElement).style.boxShadow = `0 12px 32px ${tint(mode.color, "22")}, 0 0 0 1px ${tint(mode.color, "30")}`;
              (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLDivElement).style.boxShadow = "";
              (e.currentTarget as HTMLDivElement).style.transform = "";
            }}
          >
            {/* Card header */}
            <div className="flex items-start justify-between mb-4">
              <div
                className="w-12 h-12 rounded-2xl flex items-center justify-center"
                style={{ background: `${tint(mode.color, "14")}`, border: `1px solid ${tint(mode.color, "30")}` }}
              >
                <mode.icon className="w-6 h-6" style={{ color: inkOf(mode.color) }} />
              </div>
              <span
                className="text-xs font-semibold px-2.5 py-1 rounded-full"
                style={{ backgroundColor: `${tint(mode.levelColor, "14")}`, color: inkOf(mode.levelColor), border: `1px solid ${tint(mode.levelColor, "28")}` }}
              >
                {mode.level}
              </span>
            </div>

            <h2 className="text-lg font-bold mb-2" style={{ color: "var(--ink)" }}>{mode.title}</h2>
            <p className="text-sm leading-relaxed flex-1" style={{ color: "var(--muted)" }}>{mode.description}</p>

            {/* Tags */}
            <div className="flex flex-wrap gap-2 mt-4">
              {mode.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-[10px] font-medium px-2 py-0.5 rounded-md"
                  style={{ backgroundColor: `${tint(mode.color, "12")}`, color: inkOf(mode.color) }}
                >
                  {tag}
                </span>
              ))}
            </div>

            {/* Stats */}
            <div
              className="flex items-center gap-5 mt-4 pt-4"
              style={{ borderTop: "1px solid var(--line-2)" }}
            >
              <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--faint)" }}>
                <Clock className="w-3.5 h-3.5" /> {mode.duration}
              </div>
              {mode.id === "Presentation" ? (
                <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--faint)" }}>
                  <Zap className="w-3.5 h-3.5" /> Upload a deck to start
                </div>
              ) : (() => {
                const m = stats?.byMode[mode.id];
                return (
                  <>
                    <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--faint)" }}>
                      <Zap className="w-3.5 h-3.5" /> {stats ? `${m?.sessions ?? 0} done` : "—"}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--faint)" }}>
                      <Star className="w-3.5 h-3.5" />
                      Avg score: <span className="font-semibold ml-0.5" style={{ color: m?.avgScore != null ? gradeColor(m.avgScore) : "var(--faint)" }}>
                        {m?.avgScore ?? "—"}
                      </span>
                    </div>
                  </>
                );
              })()}
            </div>

            {/* CTA */}
            <button
              onClick={() => startSession(mode.id)}
              className="mt-4 w-full flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-sm text-white transition-all hover:opacity-90 active:scale-[0.98]"
              style={{ background: mode.color }}
            >
              <Play className="w-4 h-4" />
              Start Session
            </button>
          </div>
        ))}
      </div>

      {/* Next step — from the coaching plan of your latest analysed session */}
      {(() => {
        const plan = stats?.recent.find((x) => x.analysis?.recommendations.exercises.length)?.analysis?.recommendations;
        const top = plan?.exercises[0];
        if (!plan || !top) return null;
        return (
          <div className="p-5 flex flex-wrap items-center justify-between gap-4"
            style={{ background: "var(--surface-3)", border: "1px solid var(--line)" }}>
            <div className="flex items-start gap-4 min-w-0">
              <TrendingUp className="w-5 h-5 mt-0.5 flex-shrink-0" style={{ color: "var(--accent-ink)" }} />
              <div className="min-w-0">
                <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>Next focus: {top.title}</p>
                {top.evidence && <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{top.evidence}</p>}
                {top.metric_target && <p className="text-xs mt-0.5" style={{ color: "var(--ink-2)" }}>Target: {top.metric_target}</p>}
              </div>
            </div>
            <button
              onClick={() => startSession(plan.next_session_type || top.practice_type)}
              className="flex items-center gap-1.5 text-white text-sm font-semibold px-4 py-2 flex-shrink-0"
              style={{ background: "var(--accent)" }}
            >
              Practise {(plan.next_session_type || top.practice_type).toLowerCase()} <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        );
      })()}

      {/* Recent sessions (real history) */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold" style={{ color: "var(--ink)" }}>Recent sessions</h2>
          <span className="text-xs" style={{ color: "var(--faint)" }}>Open one to see its full results</span>
        </div>
        {!signedIn ? (
          <p className="text-sm" style={{ color: "var(--muted)" }}>Sign in to keep a history of your sessions and results.</p>
        ) : !stats ? (
          <p className="text-sm" style={{ color: "var(--muted)" }}>Loading…</p>
        ) : stats.recent.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--muted)" }}>No sessions yet. Pick a mode above to start your first one.</p>
        ) : (
          <ul>
            {stats.recent.map((s) => {
              const score = s.analysis?.communication_score.overall_score;
              return (
                <li key={s.id} className="flex items-center gap-4 py-3" style={{ borderTop: "1px solid var(--line-2)" }}>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium" style={{ color: "var(--ink)" }}>{s.session_type}</p>
                    <p className="text-xs" style={{ color: "var(--faint)" }}>
                      {new Date(s.created_at).toLocaleString("en-MY", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
                      {" · "}{Math.max(1, Math.round(s.duration_sec / 60))} min
                      {s.status !== "complete" && ` · ${s.status === "analyzing" ? "analysing…" : s.status === "failed" ? "analysis failed" : "not analysed"}`}
                    </p>
                  </div>
                  <span className="text-sm font-bold w-10 text-right" style={{ color: score != null ? gradeColor(score) : "var(--faint)" }}>
                    {score != null ? Math.round(score) : "—"}
                  </span>
                  {s.status === "complete" ? (
                    <button onClick={() => router.push(`/assessment?live=${s.id}`)} className="text-xs font-medium flex items-center gap-0.5" style={{ color: "var(--accent-ink)" }}>
                      Results <ChevronRight className="w-3 h-3" />
                    </button>
                  ) : (
                    <button onClick={() => startSession(s.session_type)} className="text-xs font-medium flex items-center gap-0.5" style={{ color: "var(--accent-ink)" }}>
                      Retry <ChevronRight className="w-3 h-3" />
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

    </div>
  );
}
