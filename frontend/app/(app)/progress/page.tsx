"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Trophy, Flame, TrendingUp, Clock, Zap, Award, Target, Star } from "lucide-react";

const TREND_DATA = [
  { week: "Jan W3", overall: 68, fluency: 72, pronunciation: 64, confidence: 67, eyeContact: 71, posture: 62 },
  { week: "Jan W4", overall: 70, fluency: 74, pronunciation: 66, confidence: 68, eyeContact: 72, posture: 64 },
  { week: "Feb W1", overall: 71, fluency: 75, pronunciation: 68, confidence: 70, eyeContact: 74, posture: 63 },
  { week: "Feb W2", overall: 73, fluency: 77, pronunciation: 70, confidence: 71, eyeContact: 75, posture: 65 },
  { week: "Feb W3", overall: 74, fluency: 78, pronunciation: 72, confidence: 71, eyeContact: 77, posture: 66 },
  { week: "Feb W4", overall: 75, fluency: 79, pronunciation: 73, confidence: 72, eyeContact: 78, posture: 66 },
  { week: "Mar W1", overall: 76, fluency: 80, pronunciation: 74, confidence: 72, eyeContact: 78, posture: 67 },
  { week: "Mar W2", overall: 78, fluency: 82, pronunciation: 76, confidence: 73, eyeContact: 80, posture: 68 },
];

const HEAT_SESSIONS = [
  [0,1,2,1,3,2,0],[1,0,1,2,1,0,0],[2,1,3,2,1,2,0],[0,1,0,1,2,3,1],
  [1,2,1,0,1,2,0],[3,2,2,1,2,1,0],[1,0,2,3,1,0,0],[2,1,1,2,3,2,1],
  [0,2,0,1,2,1,0],[1,1,3,2,0,1,0],[2,3,1,2,1,0,1],[1,2,2,3,2,1,0],
];

function heatColor(n: number) {
  if (n === 0) return "#F0EDE5";
  if (n === 1) return "rgba(35,52,92,0.30)";
  if (n === 2) return "rgba(35,52,92,0.60)";
  return "#23345C";
}

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const MILESTONES = [
  { title: "First Session",         done: true,  icon: Zap,    color: "#3F6B4C", date: "Jan 15" },
  { title: "7-Day Streak",          done: true,  icon: Flame,  color: "#8A5A22", date: "Jan 22" },
  { title: "10 Sessions Completed", done: true,  icon: Star,   color: "#5A5470", date: "Feb 3"  },
  { title: "Score 75+ Overall",     done: true,  icon: Target, color: "#23345C", date: "Feb 20" },
  { title: "30-Day Streak",         done: false, icon: Trophy, color: "#8C3B32", date: "In 3 days" },
  { title: "Score 85+ Overall",     done: false, icon: Award,  color: "#8A5A22", date: "Est. Apr" },
];

const LINES = [
  { key: "overall",       label: "Overall",       color: "#17233E", width: 2.5 },
  { key: "fluency",       label: "Fluency",       color: "#23345C", width: 1.5 },
  { key: "pronunciation", label: "Pronunciation", color: "#5A5470", width: 1.5 },
  { key: "confidence",    label: "Confidence",    color: "#8A5A22", width: 1.5 },
  { key: "eyeContact",    label: "Eye Contact",   color: "#3F6B4C", width: 1.5 },
  { key: "posture",       label: "Posture",       color: "#8C3B32", width: 1.5 },
] as const;

type LineKey = (typeof LINES)[number]["key"];

export default function ProgressPage() {
  const [mounted, setMounted] = useState(false);
  const [period, setPeriod] = useState<"7D" | "30D" | "3M" | "All">("30D");
  const [visible, setVisible] = useState<Record<LineKey, boolean>>({
    overall: true, fluency: false, pronunciation: false,
    confidence: false, eyeContact: false, posture: false,
  });

  useEffect(() => { setMounted(true); }, []);

  const toggleLine = (key: LineKey) => setVisible((v) => ({ ...v, [key]: !v[key] }));

  return (
    <div className="px-4 sm:px-6 py-6 sm:py-8 max-w-[1320px] mx-auto space-y-6">

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl" style={{ color: "#17181C" }}>Progress Analytics</h1>
          <p className="text-sm mt-1" style={{ color: "#9B988E" }}>
            Track your communication improvement over time
          </p>
        </div>
        <div
          className="flex gap-1 rounded-xl p-1"
          style={{ background: "#F5F2EB", border: "1px solid #E6E2D8" }}
        >
          {(["7D", "30D", "3M", "All"] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className="relative px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
              style={{ color: period === p ? "#17233E" : "#6E6C63" }}
            >
              {period === p && (
                <motion.div
                  layoutId="progress-period-pill"
                  className="absolute inset-0 rounded-lg"
                  style={{ background: "#FFFFFF", boxShadow: "0 0 0 1px rgba(35,52,92,0.25), 0 2px 8px rgba(35,52,92,0.10)" }}
                  transition={{ type: "spring", stiffness: 480, damping: 34 }}
                />
              )}
              <span className="relative">{p}</span>
            </button>
          ))}
        </div>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        {[
          { label: "Total Sessions",      value: "42",      sub: "+8 this month",   icon: Zap,        color: "#23345C" },
          { label: "Practice Hours",      value: "18h",     sub: "+3.5h this week", icon: Clock,      color: "#5A5470" },
          { label: "Current Streak",      value: "12 days", sub: "Best: 14 days",   icon: Flame,      color: "#8A5A22" },
          { label: "Overall Improvement", value: "+10 pts", sub: "vs 8 weeks ago",  icon: TrendingUp, color: "#3F6B4C" },
        ].map(({ label, value, sub, icon: Icon, color }, i) => (
          <div key={label} className="glass-card rounded-2xl p-5 slide-up" style={{ animationDelay: `${i * 0.06}s` }}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium" style={{ color: "#9B988E" }}>{label}</span>
              <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${color}18` }}>
                <Icon className="w-4 h-4" style={{ color }} />
              </div>
            </div>
            <p className="text-2xl font-bold" style={{ color: "#17181C" }}>{value}</p>
            <p className="text-xs mt-1 font-medium" style={{ color: "#3F6B4C" }}>{sub}</p>
          </div>
        ))}
      </div>

      {/* Trend Chart */}
      <div className="glass-card rounded-2xl p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-4 mb-4">
          <h2 className="text-sm font-semibold" style={{ color: "#17181C" }}>Score Trends</h2>
          <div className="flex flex-wrap gap-1.5">
            {LINES.map(({ key, label, color }) => (
              <button
                key={key}
                onClick={() => toggleLine(key)}
                className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg border transition-all"
                style={visible[key]
                  ? { backgroundColor: `${color}18`, borderColor: color, color }
                  : { borderColor: "#E6E2D8", color: "#9B988E", background: "transparent" }
                }
              >
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                {label}
              </button>
            ))}
          </div>
        </div>

        {mounted ? (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={TREND_DATA} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1EEE6" />
              <XAxis dataKey="week" tick={{ fill: "#9B988E", fontSize: 11 }} />
              <YAxis domain={[50, 100]} tick={{ fill: "#9B988E", fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: "1px solid #E6E2D8",
                  background: "#FFFFFF",
                  boxShadow: "0 8px 24px rgba(23,24,28,0.1)",
                }}
                labelStyle={{ fontSize: 12, fontWeight: 600, color: "#17181C" }}
                itemStyle={{ fontSize: 11, color: "#4B4C52" }}
              />
              {LINES.map(({ key, label, color, width }) => (
                <Line key={key} type="monotone" dataKey={key} name={label} stroke={color} strokeWidth={width} dot={false} hide={!visible[key]} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[280px] flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-[#23345C] border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>

      {/* Heatmap */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold" style={{ color: "#17181C" }}>Practice Consistency</h2>
          <div className="flex items-center gap-2">
            <span className="text-[10px]" style={{ color: "#9B988E" }}>Less</span>
            {[0, 1, 2, 3].map((n) => (
              <div key={n} className="w-3 h-3 rounded-sm" style={{ backgroundColor: heatColor(n) }} />
            ))}
            <span className="text-[10px]" style={{ color: "#9B988E" }}>More</span>
          </div>
        </div>

        <div className="flex gap-2">
          <div className="flex flex-col gap-1 pt-1 justify-between" style={{ height: 7 * (12 + 4) - 4 }}>
            {DAY_LABELS.map((d) => (
              <span key={d} className="text-[9px] w-7 text-right leading-3" style={{ color: "#9B988E" }}>{d}</span>
            ))}
          </div>
          <div className="flex gap-1">
            {HEAT_SESSIONS.map((week, wi) => (
              <div key={wi} className="flex flex-col gap-1">
                {week.map((sessions, di) => (
                  <div
                    key={di}
                    title={`${sessions} session${sessions !== 1 ? "s" : ""}`}
                    className="w-[14px] h-[14px] rounded-[3px] cursor-default transition-opacity hover:opacity-75"
                    style={{ backgroundColor: heatColor(sessions) }}
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Milestones */}
      <div className="glass-card rounded-2xl p-6">
        <h2 className="text-sm font-semibold mb-4" style={{ color: "#17181C" }}>Milestones</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {MILESTONES.map(({ title, done, icon: Icon, color, date }) => (
            <div
              key={title}
              className="flex items-center gap-3 p-4 rounded-xl border transition-all"
              style={{
                background: done ? `${color}0c` : "#F6F3EC",
                borderColor: done ? `${color}30` : "#F0EDE5",
                opacity: done ? 1 : 0.6,
              }}
            >
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ backgroundColor: done ? `${color}18` : "#F1EEE6" }}
              >
                <Icon className="w-4 h-4" style={{ color: done ? color : "#9B988E" }} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold truncate" style={{ color: "#17181C" }}>{title}</p>
                <p className="text-[10px] mt-0.5 truncate" style={{ color: "#9B988E" }}>
                  {done ? `Achieved ${date}` : date}
                </p>
              </div>
              {done && (
                <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
