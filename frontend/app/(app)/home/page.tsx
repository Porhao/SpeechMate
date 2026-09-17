"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Users, Briefcase, Presentation, BookOpen,
  ChevronRight, Activity, Flame, Zap, Clock,
} from "lucide-react";
import { useUserStore } from "@/store/useUserStore";

// ── Mode definitions ──────────────────────────────────────────────────────────
const MODES = [
  {
    id: "Conversation",
    icon: Users,
    title: "Conversation",
    subtitle: "Natural English chat",
    desc: "Practice real conversations. AI responds to exactly what you say — adapts to every answer.",
    color: "#23345C",
    dark: "#17233E",
    glow: "rgba(35,52,92,0.5)",
    sessions: 20,
  },
  {
    id: "Interview",
    icon: Briefcase,
    title: "Interview Prep",
    subtitle: "Mock job interviews",
    desc: "Face structured behavioural questions with real-time professional coaching and STAR feedback.",
    color: "#5A5470",
    dark: "#48435C",
    glow: "rgba(90,84,112,0.5)",
    sessions: 12,
  },
  {
    id: "Presentation",
    icon: Presentation,
    title: "Presentation",
    subtitle: "Public speaking coach",
    desc: "Build confidence delivering slides and research with structured AI guidance and signpost coaching.",
    color: "#8A5A22",
    dark: "#6B4419",
    glow: "rgba(138,90,34,0.5)",
    sessions: 10,
  },
  {
    id: "Pronunciation",
    icon: BookOpen,
    title: "Pronunciation",
    subtitle: "Accent & clarity training",
    desc: "Master English phonemes with AI scoring, repeat-after-me drills, and instant accuracy feedback.",
    color: "#3F6B4C",
    dark: "#2E4F38",
    glow: "rgba(63,107,76,0.5)",
    sessions: 6,
  },
];

// ── Mode Card ─────────────────────────────────────────────────────────────────
// Flat, confident color blocking — no 3D tilt, no specular highlight, no glow.
// The only motion is a small honest lift on hover.
function ModeCard({
  mode,
  isSelecting,
  isDimmed,
  onSelect,
  index = 0,
}: {
  mode: typeof MODES[0];
  isSelecting: boolean;
  isDimmed: boolean;
  onSelect: (id: string) => void;
  index?: number;
}) {
  const Icon = mode.icon;
  const [hovered, setHovered] = useState(false);
  const [pressed, setPressed] = useState(false);

  const transform = isSelecting
    ? "scale(0.98)"
    : pressed
    ? "scale(0.96) translateY(0px)"
    : hovered
    ? "translateY(-3px) scale(1)"
    : "translateY(0) scale(1)";

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.5, ease: "easeOut" }}
    >
    <div
      className="rounded-xl relative cursor-pointer select-none"
      style={{
        height: 268,
        transform,
        transition: pressed
          ? "transform 0.08s ease-out, opacity 0.3s ease, border-color 0.2s ease"
          : "transform 0.32s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.3s ease, border-color 0.2s ease",
        opacity: isDimmed ? 0.35 : isSelecting ? 0.7 : 1,
        background: mode.color,
        border: `1px solid ${mode.dark}`,
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => { setHovered(false); setPressed(false); }}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onClick={() => onSelect(mode.id)}
    >
      {/* Inner content */}
      <div className="relative h-full flex flex-col justify-between p-6">
        {/* Icon */}
        <Icon className="w-6 h-6 text-white/85" strokeWidth={1.6} />

        {/* Text */}
        <div>
          <p className="text-white/50 text-[11px] font-medium uppercase tracking-wide mb-1.5">
            {mode.subtitle}
          </p>
          <h3 className="font-display text-white text-[22px] leading-tight mb-2">
            {mode.title}
          </h3>
          <p className="text-white/65 text-[13px] leading-relaxed line-clamp-2">
            {mode.desc}
          </p>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.14)" }}>
          <span className="text-white/45 text-xs flex items-center gap-1.5">
            <Activity className="w-3 h-3" />
            {mode.sessions} sessions
          </span>
          <span className="flex items-center gap-1 text-sm font-medium text-white">
            Start <ChevronRight className="w-3.5 h-3.5" />
          </span>
        </div>
      </div>
    </div>
    </motion.div>
  );
}

// ── Quick stat chip ───────────────────────────────────────────────────────────
function StatChip({
  icon: Icon, value, label, color, index = 0,
}: {
  icon: React.ElementType; value: string; label: string; color: string; index?: number;
}) {
  return (
    <div
      className="glass-card flex items-center gap-3 px-5 py-3.5 rounded-2xl flex-1 slide-up"
      style={{ animationDelay: `${0.3 + index * 0.06}s` }}
    >
      <div
        className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: `${color}16` }}
      >
        <Icon className="w-4.5 h-4.5" style={{ color }} />
      </div>
      <div>
        <p className="text-base font-bold leading-none" style={{ color: "#17181C" }}>{value}</p>
        <p className="text-[11px] mt-0.5" style={{ color: "#9B988E" }}>{label}</p>
      </div>
    </div>
  );
}

// ── Home / Launcher Page ──────────────────────────────────────────────────────
export default function HomePage() {
  const { user }    = useUserStore();
  const router      = useRouter();
  const [selecting, setSelecting] = useState<string | null>(null);
  const [pageOut,   setPageOut]   = useState(false);

  const firstName = user?.full_name?.split(" ")[0] ?? "there";

  const handleSelect = useCallback(
    (modeId: string) => {
      if (selecting) return;
      setSelecting(modeId);
      setTimeout(() => setPageOut(true), 260);
      setTimeout(() => router.push(`/session?mode=${modeId}`), 540);
    },
    [selecting, router],
  );

  return (
    <div
      className="px-4 sm:px-6 py-8 sm:py-10 max-w-[1320px] mx-auto"
      style={{
        opacity: pageOut ? 0 : 1,
        transform: pageOut ? "scale(0.97)" : "scale(1)",
        transition: "opacity 0.32s ease, transform 0.32s ease",
      }}
    >
      {/* ── Hero text ────────────────────────────────────────────────────── */}
      <div className="text-center mb-12">
        <p className="text-xs font-medium mb-3 uppercase tracking-wide" style={{ color: "#9B988E" }}>
          AI Communication Coach
        </p>
        <h1 className="font-display text-4xl sm:text-5xl leading-tight mb-4" style={{ color: "#17181C" }}>
          Hello, <span style={{ color: "#23345C" }}>{firstName}</span>
          {" "}
          <span style={{ color: "#34343A" }}>— what are we practising today?</span>
        </h1>
        <p className="text-base max-w-xl mx-auto" style={{ color: "#9B988E" }}>
          Choose a mode below. Your AI coach responds in real time to everything you say.
        </p>
      </div>

      {/* ── Mode cards ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5 mb-10">
        {MODES.map((mode, i) => (
          <ModeCard
            key={mode.id}
            mode={mode}
            index={i}
            isSelecting={selecting === mode.id}
            isDimmed={!!selecting && selecting !== mode.id}
            onSelect={handleSelect}
          />
        ))}
      </div>

      {/* ── Quick stats strip ────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatChip index={0} icon={Flame}    value="12 days"  label="Current streak"  color="#8A5A22" />
        <StatChip index={1} icon={Zap}      value="Level 2"  label="Developing communicator" color="#23345C" />
        <StatChip index={2} icon={Clock}    value="24.5 h"   label="Total practice"  color="#5A5470" />
        <StatChip index={3} icon={Activity} value="Score 78" label="Overall rating"  color="#3F6B4C" />
      </div>
    </div>
  );
}
