"use client";

import { useRouter } from "next/navigation";
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
    sessions: 20,
    avgScore: 82,
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
    sessions: 12,
    avgScore: 74,
    tags: ["Professional", "Eye Contact", "Structure"],
  },
  {
    id: "Presentation",
    title: "Presentation Practice",
    description: "Deliver speeches, academic presentations, and pitches. Real-time analysis of your posture, eye contact, speaking pace, and slide timing.",
    icon: Presentation,
    color: "#8A5A22",
    dark: "#6B4419",
    level: "Advanced",
    levelColor: "#8C3B32",
    duration: "5–60 min",
    sessions: 10,
    avgScore: 71,
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
    sessions: 6,
    avgScore: 75,
    tags: ["Phonemes", "BM English", "Accuracy"],
  },
];

const RECENT = [
  { type: "Presentation",  score: 78, duration: "45 min", date: "Today, 9:00 AM",     color: "#8A5A22" },
  { type: "Conversation",  score: 82, duration: "30 min", date: "Yesterday, 3:30 PM", color: "#23345C" },
  { type: "Interview",     score: 71, duration: "35 min", date: "Mon, 10:00 AM",      color: "#5A5470" },
  { type: "Pronunciation", score: 75, duration: "20 min", date: "Fri, 4:00 PM",       color: "#3F6B4C" },
];

function gradeColor(score: number) {
  if (score >= 90) return "#3F6B4C";
  if (score >= 80) return "#23345C";
  if (score >= 70) return "#8A5A22";
  return "#8C3B32";
}

export default function PracticePage() {
  const router = useRouter();
  const startSession = (mode: string) => router.push(`/session?mode=${encodeURIComponent(mode)}`);

  return (
    <div className="px-4 sm:px-6 py-6 sm:py-8 max-w-[1320px] mx-auto space-y-8">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl" style={{ color: "#17181C" }}>Practice Center</h1>
          <p className="text-sm mt-1" style={{ color: "#6E6C63" }}>
            Choose a mode and start improving your communication skills
          </p>
        </div>
        <div
          className="flex items-center gap-2 text-sm px-4 py-2 rounded-xl"
          style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#4B4C52" }}
        >
          <Target className="w-4 h-4" style={{ color: "#23345C" }} />
          Weekly goal: <span className="font-semibold ml-1" style={{ color: "#17181C" }}>5 sessions</span>
          <span className="font-semibold ml-1" style={{ color: "#3F6B4C" }}>· 3 done</span>
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
              (e.currentTarget as HTMLDivElement).style.boxShadow = `0 12px 32px ${mode.color}22, 0 0 0 1px ${mode.color}30`;
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
                style={{ background: `${mode.color}14`, border: `1px solid ${mode.color}30` }}
              >
                <mode.icon className="w-6 h-6" style={{ color: mode.color }} />
              </div>
              <span
                className="text-xs font-semibold px-2.5 py-1 rounded-full"
                style={{ backgroundColor: `${mode.levelColor}14`, color: mode.levelColor, border: `1px solid ${mode.levelColor}28` }}
              >
                {mode.level}
              </span>
            </div>

            <h2 className="text-lg font-bold mb-2" style={{ color: "#17181C" }}>{mode.title}</h2>
            <p className="text-sm leading-relaxed flex-1" style={{ color: "#6E6C63" }}>{mode.description}</p>

            {/* Tags */}
            <div className="flex flex-wrap gap-2 mt-4">
              {mode.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-[10px] font-medium px-2 py-0.5 rounded-md"
                  style={{ backgroundColor: `${mode.color}12`, color: mode.color }}
                >
                  {tag}
                </span>
              ))}
            </div>

            {/* Stats */}
            <div
              className="flex items-center gap-5 mt-4 pt-4"
              style={{ borderTop: "1px solid #F0EDE5" }}
            >
              <div className="flex items-center gap-1.5 text-xs" style={{ color: "#9B988E" }}>
                <Clock className="w-3.5 h-3.5" /> {mode.duration}
              </div>
              <div className="flex items-center gap-1.5 text-xs" style={{ color: "#9B988E" }}>
                <Zap className="w-3.5 h-3.5" /> {mode.sessions} sessions
              </div>
              <div className="flex items-center gap-1.5 text-xs" style={{ color: "#9B988E" }}>
                <Star className="w-3.5 h-3.5" />
                Avg: <span className="font-semibold ml-0.5" style={{ color: gradeColor(mode.avgScore) }}>{mode.avgScore}</span>
              </div>
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

      {/* Quick Start Banner */}
      <div
        className="rounded-2xl p-5 flex items-center justify-between"
        style={{ background: "#F1EEE6", border: "1px solid #E6E2D8" }}
      >
        <div className="flex items-center gap-4">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: "rgba(35,52,92,0.14)", border: "1px solid rgba(35,52,92,0.25)" }}
          >
            <TrendingUp className="w-5 h-5" style={{ color: "#23345C" }} />
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: "#17181C" }}>
              Recommended: Continue Presentation Practice
            </p>
            <p className="text-xs mt-0.5" style={{ color: "#6E6C63" }}>
              Your posture score dropped last session — 10 min daily will bring it back up
            </p>
          </div>
        </div>
        <button
          onClick={() => startSession("Presentation")}
          className="flex items-center gap-1.5 text-white text-sm font-semibold px-4 py-2 rounded-xl transition-colors flex-shrink-0"
          style={{ background: "#23345C" }}
        >
          Start now <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Recent Sessions */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold" style={{ color: "#17181C" }}>Recent Sessions</h2>
          <span className="text-xs" style={{ color: "#9B988E" }}>Last 7 days</span>
        </div>
        <div className="space-y-2">
          {RECENT.map((s, i) => (
            <div
              key={i}
              className="flex items-center gap-4 p-3 rounded-xl transition-colors"
              style={{ cursor: "default" }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = "#F5F2EB"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
            >
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ backgroundColor: `${s.color}14`, border: `1px solid ${s.color}25` }}
              >
                <Zap className="w-4 h-4" style={{ color: s.color }} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium" style={{ color: "#17181C" }}>{s.type}</p>
                <p className="text-xs" style={{ color: "#9B988E" }}>{s.date} · {s.duration}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-bold" style={{ color: gradeColor(s.score) }}>{s.score}</span>
                <button
                  onClick={() => startSession(s.type)}
                  className="text-xs font-medium flex items-center gap-0.5 transition-colors"
                  style={{ color: "#23345C" }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = "#17233E"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = "#23345C"; }}
                >
                  Retry <ChevronRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
