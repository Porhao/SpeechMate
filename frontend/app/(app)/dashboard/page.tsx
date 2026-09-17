"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import {
  Flame, Clock, BarChart2, TrendingUp, TrendingDown, Minus,
  ChevronRight, Award, Zap, Trophy, Eye, Volume2, Lock,
  Activity, Star, Target, Mic,
} from "lucide-react";
import { useUserStore } from "@/store/useUserStore";
import { AnimatedNumber } from "@/components/ui/AnimatedNumber";

// ── Mock data ─────────────────────────────────────────────────────────────────
const RADAR_DATA = [
  { subject: "Fluency",       current: 84, previous: 79 },
  { subject: "Pronunciation", current: 76, previous: 74 },
  { subject: "Confidence",    current: 72, previous: 73 },
  { subject: "Eye Contact",   current: 80, previous: 77 },
  { subject: "Posture",       current: 68, previous: 63 },
  { subject: "Presentation",  current: 74, previous: 68 },
];

const PROGRESS_DATA = [
  { week: "Wk 1", Fluency: 72, Pronunciation: 70, Confidence: 65, "Eye Contact": 68 },
  { week: "Wk 2", Fluency: 76, Pronunciation: 72, Confidence: 68, "Eye Contact": 72 },
  { week: "Wk 3", Fluency: 80, Pronunciation: 74, Confidence: 70, "Eye Contact": 76 },
  { week: "Wk 4", Fluency: 84, Pronunciation: 76, Confidence: 72, "Eye Contact": 80 },
];

const METRIC_LINES = [
  { key: "Fluency",       color: "#23345C" },
  { key: "Pronunciation", color: "#5A5470" },
  { key: "Confidence",    color: "#8A5A22" },
  { key: "Eye Contact",   color: "#3F6B4C" },
];

const RECENT_SESSIONS = [
  { type: "Presentation",   duration: "45 min", score: 78, time: "Today, 9:00 AM",     color: "#8A5A22" },
  { type: "Conversation",   duration: "30 min", score: 82, time: "Yesterday, 3:30 PM", color: "#23345C" },
  { type: "Interview Prep", duration: "35 min", score: 71, time: "Mon, 10:00 AM",      color: "#23345C" },
  { type: "Pronunciation",  duration: "20 min", score: 75, time: "Fri, 4:00 PM",       color: "#386B4F" },
];

const ACHIEVEMENTS = [
  { title: "First Session",      desc: "Complete your first session",   unlocked: true,  Icon: Zap,        xp: 50  },
  { title: "7-Day Streak",       desc: "Practice 7 consecutive days",   unlocked: true,  Icon: Flame,      xp: 100 },
  { title: "Fluency Pro",        desc: "Reach 80+ fluency score",       unlocked: true,  Icon: TrendingUp, xp: 150 },
  { title: "30-Day Streak",      desc: "Practice 30 consecutive days",  unlocked: false, Icon: Trophy,     xp: 300 },
  { title: "Eye Contact Master", desc: "Reach 90+ eye contact score",   unlocked: false, Icon: Eye,        xp: 200 },
  { title: "Pronunciation Pro",  desc: "Reach 90+ pronunciation score", unlocked: false, Icon: Award,      xp: 250 },
];

// ── Helpers ───────────────────────────────────────────────────────────────────
function gradeColor(s: number) {
  return s >= 90 ? "#3F6B4C" : s >= 80 ? "#23345C" : s >= 70 ? "#8A5A22" : "#8C3B32";
}
function gradeLabel(s: number) {
  return s >= 90 ? "Excellent" : s >= 80 ? "Very Good" : s >= 70 ? "Good" : "Needs Work";
}
function pctChange(cur: number, prev: number) {
  return Math.round(((cur - prev) / prev) * 100);
}
function timeGreeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

// ── Score gauge ───────────────────────────────────────────────────────────────
function ScoreGauge({ score }: { score: number }) {
  const r = 42, circ = 2 * Math.PI * r;
  const color = gradeColor(score);
  return (
    <svg width="110" height="110" viewBox="0 0 110 110" className="flex-shrink-0">
      <circle cx="55" cy="55" r={r} fill="none" stroke="#F0EDE5" strokeWidth="8" />
      <motion.circle cx="55" cy="55" r={r} fill="none" stroke={color} strokeWidth="8"
        strokeLinecap="round" transform="rotate(-90 55 55)"
        initial={{ strokeDasharray: `0 ${circ}` }}
        animate={{ strokeDasharray: `${(score / 100) * circ} ${circ}` }}
        transition={{ duration: 1.1, ease: "easeOut", delay: 0.1 }}
      />
      <text x="55" y="50" textAnchor="middle" fill="#17181C" fontSize="20" fontWeight="700">{score}</text>
      <text x="55" y="65" textAnchor="middle" fill={color} fontSize="9" fontWeight="600">{gradeLabel(score)}</text>
    </svg>
  );
}

// ── Dashboard / Analytics Page ────────────────────────────────────────────────
export default function DashboardPage() {
  const { user }   = useUserStore();
  const [mounted,  setMounted]  = useState(false);
  const [activeLines, setActiveLines] = useState<Record<string, boolean>>(
    Object.fromEntries(METRIC_LINES.map((m) => [m.key, true])),
  );

  useEffect(() => { setMounted(true); }, []);

  const firstName    = user?.full_name?.split(" ")[0] ?? "there";
  const overallScore = 78;

  const toggleLine = (key: string) =>
    setActiveLines((p) => ({ ...p, [key]: !p[key] }));

  return (
    <div className="px-4 sm:px-6 py-6 sm:py-8 max-w-[1320px] mx-auto space-y-6">

      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl" style={{ color: "#17181C" }}>
            {timeGreeting()},&nbsp;
            <span style={{ color: "#23345C" }}>{firstName}</span>
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "#9B988E" }}>Here's your communication progress.</p>
        </div>

        {/* Streak + Level — high-contrast badges */}
        <div className="flex items-center gap-2 flex-wrap">
          <div
            className="flex items-center gap-2 px-4 py-2 rounded-xl"
            style={{
              background: "rgba(138,90,34,0.10)",
              border: "1px solid rgba(138,90,34,0.25)",
            }}
          >
            <Flame className="w-4 h-4" style={{ color: "#8A5A22" }} />
            <span className="text-sm font-semibold" style={{ color: "#6B4419" }}>12-day streak</span>
          </div>
          <div
            className="flex items-center gap-2 px-4 py-2 rounded-xl"
            style={{
              background: "rgba(35,52,92,0.10)",
              border: "1px solid rgba(35,52,92,0.25)",
            }}
          >
            <Zap className="w-4 h-4" style={{ color: "#23345C" }} />
            <span className="text-sm font-semibold" style={{ color: "#17233E" }}>Level 2 · Developing</span>
          </div>
          <Link
            href="/home"
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all press-effect"
            style={{ background: "#23345C" }}
          >
            <Mic className="w-4 h-4" /> Start Practice
          </Link>
        </div>
      </div>

      {/* ── KPI cards row ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Overall Score */}
        <div className="glass-card rounded-2xl p-5 flex items-center gap-4 slide-up" style={{ animationDelay: "0s" }}>
          <ScoreGauge score={overallScore} />
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: "#9B988E" }}>Overall</p>
            <p className="text-sm leading-snug" style={{ color: "#4B4C52" }}>Communication<br />Performance</p>
            <p className="text-xs font-semibold mt-2 flex items-center gap-1" style={{ color: "#3F6B4C" }}>
              <TrendingUp className="w-3 h-3" /> +4.7% this week
            </p>
          </div>
        </div>

        {/* Streak */}
        <div className="glass-card rounded-2xl p-5 slide-up" style={{ animationDelay: "0.05s" }}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "#9B988E" }}>Streak</p>
            <div className="w-8 h-8 rounded-xl flex items-center justify-center"
              style={{ background: "rgba(138,90,34,0.10)" }}>
              <Flame className="w-4 h-4" style={{ color: "#8A5A22" }} />
            </div>
          </div>
          <p className="text-3xl font-bold" style={{ color: "#17181C" }}>
            <AnimatedNumber value={12} /> <span className="text-sm font-normal" style={{ color: "#9B988E" }}>days</span>
          </p>
          <div className="mt-3 space-y-1.5">
            <div className="flex justify-between text-xs">
              <span style={{ color: "#9B988E" }}>Longest streak</span>
              <span className="font-semibold" style={{ color: "#34343A" }}>24 days</span>
            </div>
            <div className="flex justify-between text-xs">
              <span style={{ color: "#9B988E" }}>Total days</span>
              <span className="font-semibold" style={{ color: "#34343A" }}>38 days</span>
            </div>
          </div>
        </div>

        {/* Practice Time */}
        <div className="glass-card rounded-2xl p-5 slide-up" style={{ animationDelay: "0.1s" }}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "#9B988E" }}>Practice Time</p>
            <div className="w-8 h-8 rounded-xl flex items-center justify-center"
              style={{ background: "rgba(35,52,92,0.10)" }}>
              <Clock className="w-4 h-4" style={{ color: "#23345C" }} />
            </div>
          </div>
          <p className="text-3xl font-bold" style={{ color: "#17181C" }}>
            <AnimatedNumber value={24.5} decimals={1} /> <span className="text-sm font-normal" style={{ color: "#9B988E" }}>hours</span>
          </p>
          <div className="mt-3 space-y-1.5">
            <div className="flex justify-between text-xs">
              <span style={{ color: "#9B988E" }}>This week</span>
              <span className="font-semibold" style={{ color: "#34343A" }}>3.2 hours</span>
            </div>
            <div className="flex justify-between text-xs">
              <span style={{ color: "#9B988E" }}>This month</span>
              <span className="font-semibold" style={{ color: "#34343A" }}>14.8 hours</span>
            </div>
          </div>
        </div>

        {/* Sessions */}
        <div className="glass-card rounded-2xl p-5 slide-up" style={{ animationDelay: "0.15s" }}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "#9B988E" }}>Sessions</p>
            <div className="w-8 h-8 rounded-xl flex items-center justify-center"
              style={{ background: "rgba(35,52,92,0.10)" }}>
              <BarChart2 className="w-4 h-4" style={{ color: "#23345C" }} />
            </div>
          </div>
          <p className="text-3xl font-bold" style={{ color: "#17181C" }}>
            <AnimatedNumber value={48} /> <span className="text-sm font-normal" style={{ color: "#9B988E" }}>total</span>
          </p>
          <div className="mt-3 grid grid-cols-2 gap-y-1.5 text-xs">
            {[["Conversation", 20], ["Interview", 12], ["Presentation", 10], ["Pronunciation", 6]].map(
              ([type, count]) => (
                <div key={String(type)} className="flex justify-between gap-2">
                  <span style={{ color: "#9B988E" }}>{type}</span>
                  <span className="font-semibold" style={{ color: "#34343A" }}>{count}</span>
                </div>
              ),
            )}
          </div>
        </div>
      </div>

      {/* ── Skill health bars ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-4">
        {[
          { label: "Fluency",       score: 84, prev: 79, color: "#23345C" },
          { label: "Pronunciation", score: 76, prev: 74, color: "#5A5470" },
          { label: "Confidence",    score: 72, prev: 73, color: "#8A5A22" },
          { label: "Eye Contact",   score: 80, prev: 77, color: "#3F6B4C" },
          { label: "Posture",       score: 68, prev: 63, color: "#8C3B32" },
        ].map(({ label, score, prev, color }, i) => {
          const change = pctChange(score, prev);
          const up = change > 0, flat = change === 0;
          return (
            <div key={label} className="glass-card rounded-2xl p-4 slide-up" style={{ animationDelay: `${i * 0.05}s` }}>
              <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "#9B988E" }}>{label}</p>
              <div className="flex items-end gap-1.5 mb-2">
                <span className="text-2xl font-bold" style={{ color }}><AnimatedNumber value={score} duration={1 + i * 0.1} /></span>
                <span className="text-xs mb-0.5" style={{ color: "#CDC9BE" }}>/ 100</span>
              </div>
              <div className="h-1.5 rounded-full mb-3 overflow-hidden" style={{ background: "#F0EDE5" }}>
                <div className="h-full rounded-full transition-all duration-1000 ease-out" style={{ width: mounted ? `${score}%` : "0%", backgroundColor: color }} />
              </div>
              <div className="flex items-center justify-between text-xs">
                <span style={{ color: "#9B988E" }}>Prev: {prev}</span>
                <span className="flex items-center gap-0.5 font-semibold" style={{ color: flat ? "#9B988E" : up ? "#3F6B4C" : "#8C3B32" }}>
                  {flat ? <Minus className="w-3 h-3" /> : up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                  {flat ? "0%" : `${up ? "+" : ""}${change}%`}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Radar + Recent sessions ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Radar */}
        <div className="xl:col-span-2 glass-card rounded-2xl p-6">
          <h2 className="text-base font-semibold mb-0.5" style={{ color: "#17181C" }}>Communication Radar</h2>
          <p className="text-xs mb-5" style={{ color: "#9B988E" }}>Holistic view across 6 skill dimensions</p>
          {mounted ? (
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={RADAR_DATA} margin={{ top: 16, right: 40, bottom: 16, left: 40 }}>
                <PolarGrid stroke="#F0EDE5" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: "#6E6C63", fontSize: 10, fontWeight: 500 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar name="Previous" dataKey="previous" stroke="#CDC9BE" fill="#F1EEE6" fillOpacity={1} strokeWidth={1.5} strokeDasharray="4 2" />
                <Radar name="Current"  dataKey="current"  stroke="#23345C" fill="#23345C" fillOpacity={0.16} strokeWidth={2} />
                <Legend iconType="line" iconSize={14} formatter={(v) => <span style={{ color: "#6E6C63", fontSize: 11 }}>{v}</span>} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #E6E2D8", background: "#FFFFFF", color: "#17181C", fontSize: 12, boxShadow: "0 8px 24px rgba(23,24,28,0.1)" }} />
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[280px] flex items-center justify-center">
              <div className="w-7 h-7 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "#23345C", borderTopColor: "transparent" }} />
            </div>
          )}
        </div>

        {/* Recent Sessions */}
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold" style={{ color: "#17181C" }}>Recent Sessions</h2>
            <Link href="/home" className="text-xs font-medium flex items-center gap-0.5 transition-colors" style={{ color: "#23345C" }}>
              New session <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="space-y-1.5">
            {RECENT_SESSIONS.map((s, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all"
                style={{ background: "#F6F3EC" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "#F1EEE6")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "#F6F3EC")}>
                <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: `${s.color}16` }}>
                  <Activity className="w-4 h-4" style={{ color: s.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: "#24252B" }}>{s.type}</p>
                  <p className="text-xs" style={{ color: "#9B988E" }}>{s.time} · {s.duration}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-bold" style={{ color: gradeColor(s.score) }}>{s.score}</p>
                  <p className="text-[10px]" style={{ color: "#CDC9BE" }}>{gradeLabel(s.score)}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4" style={{ borderTop: "1px solid #F0EDE5" }}>
            <p className="text-[10px] font-semibold uppercase tracking-wider mb-3" style={{ color: "#9B988E" }}>This Week</p>
            <div className="grid grid-cols-3 gap-2 text-center">
              {[{ label: "Sessions", value: "4" }, { label: "Hours", value: "2.2h" }, { label: "Avg Score", value: "77" }].map(({ label, value }) => (
                <div key={label} className="rounded-xl py-2.5"
                  style={{ background: "rgba(35,52,92,0.07)", border: "1px solid rgba(35,52,92,0.14)" }}>
                  <p className="text-sm font-bold" style={{ color: "#17181C" }}>{value}</p>
                  <p className="text-[10px]" style={{ color: "#9B988E" }}>{label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Progress trends ───────────────────────────────────────────────── */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
          <div>
            <h2 className="text-base font-semibold" style={{ color: "#17181C" }}>Progress Trends</h2>
            <p className="text-xs mt-0.5" style={{ color: "#9B988E" }}>4-week history — click a metric to toggle</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {METRIC_LINES.map(({ key, color }) => (
              <button key={key} onClick={() => toggleLine(key)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all"
                style={activeLines[key]
                  ? { background: `${color}12`, color, borderColor: `${color}30` }
                  : { background: "transparent", color: "#CDC9BE", borderColor: "#E6E2D8" }}>
                <span className="w-2 h-2 rounded-full" style={{ background: color }} />{key}
              </button>
            ))}
          </div>
        </div>
        {mounted ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={PROGRESS_DATA} margin={{ left: -20, right: 8, top: 4, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1EEE6" vertical={false} />
              <XAxis dataKey="week" tick={{ fill: "#9B988E", fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis domain={[50, 100]} tick={{ fill: "#9B988E", fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #E6E2D8", background: "#FFFFFF", color: "#17181C", fontSize: 12, boxShadow: "0 8px 24px rgba(23,24,28,0.1)" }} />
              {METRIC_LINES.map(({ key, color }) => (
                <Line key={key} type="monotone" dataKey={key} stroke={color} strokeWidth={2} hide={!activeLines[key]}
                  dot={{ fill: color, r: 3, strokeWidth: 0 }} activeDot={{ r: 5, strokeWidth: 0, fill: color }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[220px] flex items-center justify-center">
            <div className="w-7 h-7 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "#23345C", borderTopColor: "transparent" }} />
          </div>
        )}
        <div className="mt-4 pt-4 flex items-center gap-3" style={{ borderTop: "1px solid #F1EEE6" }}>
          <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: "rgba(35,52,92,0.10)" }}>
            <TrendingUp className="w-4 h-4" style={{ color: "#23345C" }} />
          </div>
          <p className="text-xs" style={{ color: "#9B988E" }}>
            <span className="font-semibold" style={{ color: "#4B4C52" }}>Forecast:</span> At your current pace,
            your score is predicted to reach{" "}
            <span className="font-semibold" style={{ color: "#23345C" }}>90</span> within 4 weeks.
          </p>
        </div>
      </div>

      {/* ── Level + Achievements ─────────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 pb-6">
        {/* Level card */}
        <div
          className="rounded-2xl p-6 text-white overflow-hidden relative"
          style={{ background: "#23345C" }}
        >
          <div className="relative flex items-center justify-between mb-5">
            <div>
              <p className="text-xs font-medium mb-0.5" style={{ color: "#E8E9EF" }}>Your Level</p>
              <p className="text-xl font-bold">Level 2 · Developing Communicator</p>
            </div>
            <div className="w-12 h-12 bg-white/15 rounded-xl flex items-center justify-center flex-shrink-0">
              <Zap className="w-6 h-6 text-white" />
            </div>
          </div>
          <div className="relative flex items-center justify-between text-xs mb-2" style={{ color: "#E8E9EF" }}>
            <span>Progress to Level 3</span><span>680 / 1000 XP</span>
          </div>
          <div className="relative h-2 bg-white/15 rounded-full mb-2">
            <div className="h-full bg-white rounded-full" style={{ width: "68%" }} />
          </div>
          <p className="relative text-xs" style={{ color: "#E8E9EF" }}>320 XP remaining to Confident Speaker</p>

          {/* Recommendations */}
          <div className="relative mt-5 pt-5" style={{ borderTop: "1px solid rgba(255,255,255,0.15)" }}>
            <p className="text-xs font-semibold mb-3" style={{ color: "#E8E9EF" }}>Recommended for you</p>
            <div className="space-y-2">
              {[
                { title: "Power Stance Drill",   metric: "Posture",    min: 10, icon: Target },
                { title: "Mock Presentations",   metric: "Confidence", min: 15, icon: Mic    },
              ].map(({ title, metric, min, icon: Ic }) => (
                <div key={title} className="flex items-center gap-3 p-3 rounded-xl"
                  style={{ background: "rgba(255,255,255,0.12)" }}>
                  <Ic className="w-4 h-4 flex-shrink-0" style={{ color: "#E8E9EF" }} />
                  <div>
                    <p className="text-xs font-semibold text-white">{title}</p>
                    <p className="text-[10px]" style={{ color: "#E8E9EF" }}>{min} min/day · {metric}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Achievements */}
        <div className="glass-card rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold" style={{ color: "#17181C" }}>Achievements</h2>
            <span className="text-xs" style={{ color: "#9B988E" }}>3 / 6 unlocked</span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {ACHIEVEMENTS.map(({ title, desc, unlocked, Icon, xp }) => (
              <div key={title} title={desc}
                className="flex flex-col items-center gap-1.5 p-3 rounded-xl text-center border transition-all"
                style={unlocked
                  ? { background: "rgba(35,52,92,0.08)", borderColor: "rgba(35,52,92,0.22)" }
                  : { background: "#F6F3EC", borderColor: "#F0EDE5", opacity: 0.55 }}>
                <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: unlocked ? "#23345C" : "#E6E2D8" }}>
                  {unlocked ? <Icon className="w-4 h-4 text-white" /> : <Lock className="w-4 h-4" style={{ color: "#9B988E" }} />}
                </div>
                <p className="text-[10px] font-semibold leading-tight" style={{ color: "#34343A" }}>{title}</p>
                <p className="text-[9px]" style={{ color: "#9B988E" }}>+{xp} XP</p>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 flex items-center justify-between" style={{ borderTop: "1px solid #F1EEE6" }}>
            <p className="text-xs" style={{ color: "#9B988E" }}>XP earned this week</p>
            <div className="flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5" style={{ color: "#8A5A22" }} />
              <span className="text-sm font-bold" style={{ color: "#17181C" }}>+120 XP</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
