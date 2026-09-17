"use client";

import { useState } from "react";
import { Save, Check, Zap, Clock, Trophy, Target } from "lucide-react";
import { useUserStore } from "@/store/useUserStore";

const LANGUAGE_OPTIONS = [
  { value: "English",         label: "English" },
  { value: "Bahasa Malaysia", label: "Bahasa Malaysia" },
  { value: "Bilingual",       label: "Bilingual (BM + English)" },
];

const GOAL_OPTIONS = [
  { value: "Academic Presentations", label: "Academic Presentations" },
  { value: "Job Interviews",         label: "Job Interviews" },
  { value: "Public Speaking",        label: "Public Speaking" },
  { value: "Business Communication", label: "Business Communication" },
  { value: "Daily Conversation",     label: "Daily Conversation" },
];

const SKILL_OPTIONS = ["Beginner", "Intermediate", "Advanced"] as const;

const CHALLENGE_OPTIONS = [
  "Filler Words", "Pronunciation", "Eye Contact",
  "Speaking Pace", "Confidence", "Posture",
] as const;

type SkillLevel = (typeof SKILL_OPTIONS)[number];

function Avatar({ name, size = 72 }: { name: string; size?: number }) {
  const initials = name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2);
  return (
    <div
      className="rounded-full flex items-center justify-center text-white font-bold flex-shrink-0"
      style={{ width: size, height: size, background: "#23345C", fontSize: size * 0.3 }}
    >
      {initials}
    </div>
  );
}

export default function ProfilePage() {
  const { user, profile, setUser, setProfile } = useUserStore();

  const [name,       setName]       = useState(user?.full_name ?? "Ahmad Rizwan");
  const [language,   setLanguage]   = useState(user?.language ?? "Bilingual");
  const [goal,       setGoal]       = useState(profile?.communication_goal ?? "Academic Presentations");
  const [skill,      setSkill]      = useState<SkillLevel>((profile?.skill_level as SkillLevel) ?? "Intermediate");
  const [challenges, setChallenges] = useState<string[]>(profile?.challenges ?? ["Eye Contact", "Confidence"]);
  const [saved,      setSaved]      = useState(false);

  const toggleChallenge = (c: string) =>
    setChallenges((prev) => prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]);

  const handleSave = () => {
    if (user) setUser({ ...user, full_name: name, language });
    if (profile) setProfile({ ...profile, communication_goal: goal, skill_level: skill as "Beginner" | "Intermediate" | "Advanced", challenges });
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="px-4 sm:px-6 py-6 sm:py-8 max-w-[1320px] mx-auto space-y-6">

      {/* Header */}
      <div>
        <h1 className="font-display text-2xl" style={{ color: "#17181C" }}>Profile</h1>
        <p className="text-sm mt-1" style={{ color: "#9B988E" }}>
          Manage your account and communication goals
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6 items-start">

        {/* Left: avatar + stats */}
        <div className="space-y-4">
          <div className="glass-card rounded-2xl p-6 flex flex-col items-center text-center">
            <Avatar name={name} size={80} />
            <p className="text-lg font-bold mt-4" style={{ color: "#17181C" }}>{name}</p>
            <p className="text-sm mt-0.5" style={{ color: "#9B988E" }}>{user?.email ?? "ahmad@example.com"}</p>

            <div className="flex items-center gap-2 mt-3">
              <span
                className="text-xs font-semibold px-2.5 py-1 rounded-full"
                style={{ background: "rgba(35,52,92,0.12)", border: "1px solid rgba(35,52,92,0.28)", color: "#17233E" }}
              >
                {skill}
              </span>
              <span
                className="text-xs font-semibold px-2.5 py-1 rounded-full"
                style={{ background: "rgba(90,84,112,0.10)", border: "1px solid rgba(90,84,112,0.22)", color: "#48435C" }}
              >
                {language}
              </span>
            </div>

            <div className="w-full mt-5 pt-5 space-y-3" style={{ borderTop: "1px solid #F0EDE5" }}>
              {[
                { label: "Total Sessions", value: "42",    icon: Zap,    color: "#23345C" },
                { label: "Practice Hours", value: "18h",   icon: Clock,  color: "#5A5470" },
                { label: "Current Level",  value: "Lv 5",  icon: Trophy, color: "#8A5A22" },
                { label: "Total XP",       value: "2,340", icon: Target, color: "#3F6B4C" },
              ].map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icon className="w-3.5 h-3.5" style={{ color }} />
                    <span className="text-xs" style={{ color: "#6E6C63" }}>{label}</span>
                  </div>
                  <span className="text-sm font-bold" style={{ color: "#17181C" }}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          <div
            className="rounded-2xl px-5 py-4"
            style={{ background: "rgba(35,52,92,0.06)", border: "1px solid rgba(35,52,92,0.16)" }}
          >
            <p className="text-xs leading-relaxed" style={{ color: "#6E6C63" }}>
              Member since <strong style={{ color: "#17181C" }}>January 2026</strong>.
              Your data is protected under Malaysia PDPA.
            </p>
          </div>
        </div>

        {/* Right: edit form */}
        <div className="glass-card rounded-2xl p-6 space-y-6">

          {/* Personal Info */}
          <div>
            <h2 className="text-sm font-semibold mb-4" style={{ color: "#17181C" }}>Personal Information</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: "#6E6C63" }}>Full Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl text-sm outline-none transition-all placeholder:text-slate-400"
                  style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#17181C" }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(35,52,92,0.5)"; }}
                  onBlur={(e) => { e.currentTarget.style.borderColor = "#E6E2D8"; }}
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: "#6E6C63" }}>Email Address</label>
                <input
                  type="email"
                  value={user?.email ?? "ahmad@example.com"}
                  readOnly
                  className="w-full px-3 py-2.5 rounded-xl text-sm cursor-not-allowed"
                  style={{ background: "#F1EEE6", border: "1px solid #E6E2D8", color: "#9B988E" }}
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: "#6E6C63" }}>Language Preference</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl text-sm outline-none transition-all"
                  style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#17181C" }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(35,52,92,0.5)"; }}
                  onBlur={(e) => { e.currentTarget.style.borderColor = "#E6E2D8"; }}
                >
                  {LANGUAGE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div style={{ borderTop: "1px solid #F0EDE5" }} />

          {/* Communication Goal */}
          <div>
            <h2 className="text-sm font-semibold mb-4" style={{ color: "#17181C" }}>Communication Goal</h2>
            <div className="grid grid-cols-1 gap-2">
              {GOAL_OPTIONS.map((o) => (
                <label
                  key={o.value}
                  className="flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all"
                  style={{
                    borderColor: goal === o.value ? "rgba(35,52,92,0.5)" : "#E6E2D8",
                    background: goal === o.value ? "rgba(35,52,92,0.08)" : "#F6F3EC",
                  }}
                >
                  <input
                    type="radio"
                    name="goal"
                    value={o.value}
                    checked={goal === o.value}
                    onChange={() => setGoal(o.value)}
                    className="accent-[#23345C]"
                  />
                  <span className="text-sm" style={{ color: "#17181C" }}>{o.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div style={{ borderTop: "1px solid #F0EDE5" }} />

          {/* Skill Level */}
          <div>
            <h2 className="text-sm font-semibold mb-4" style={{ color: "#17181C" }}>Skill Level</h2>
            <div className="flex gap-3">
              {SKILL_OPTIONS.map((s) => {
                const colors: Record<SkillLevel, string> = { Beginner: "#3F6B4C", Intermediate: "#8A5A22", Advanced: "#8C3B32" };
                const active = skill === s;
                const c = colors[s];
                return (
                  <button
                    key={s}
                    onClick={() => setSkill(s)}
                    className="flex-1 py-2.5 rounded-xl border text-sm font-semibold transition-all"
                    style={active
                      ? { backgroundColor: `${c}14`, borderColor: c, color: c }
                      : { borderColor: "#E6E2D8", color: "#9B988E", background: "#F6F3EC" }
                    }
                  >
                    {s}
                  </button>
                );
              })}
            </div>
          </div>

          <div style={{ borderTop: "1px solid #F0EDE5" }} />

          {/* Challenges */}
          <div>
            <h2 className="text-sm font-semibold mb-1" style={{ color: "#17181C" }}>Main Challenges</h2>
            <p className="text-xs mb-3" style={{ color: "#9B988E" }}>Select all that apply</p>
            <div className="flex flex-wrap gap-2">
              {CHALLENGE_OPTIONS.map((c) => {
                const active = challenges.includes(c);
                return (
                  <button
                    key={c}
                    onClick={() => toggleChallenge(c)}
                    className="px-3 py-1.5 rounded-full text-xs font-semibold border transition-all"
                    style={active
                      ? { background: "rgba(35,52,92,0.14)", borderColor: "#23345C", color: "#17233E" }
                      : { borderColor: "#E6E2D8", color: "#9B988E", background: "#F6F3EC" }
                    }
                  >
                    {c}
                  </button>
                );
              })}
            </div>
          </div>

          <div style={{ borderTop: "1px solid #F0EDE5" }} />

          {/* Save */}
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold text-white transition-all press-effect"
              style={{ background: saved ? "#3F6B4C" : "#23345C" }}
            >
              {saved ? <><Check className="w-4 h-4" /> Saved!</> : <><Save className="w-4 h-4" /> Save Changes</>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
