"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronRight,
  ChevronLeft,
  CheckCircle2,
  Mic,
  Briefcase,
  Presentation,
  Volume2,
  Zap,
  Target,
  Users,
  MessageCircle,
  Eye,
  Activity,
  Brain,
} from "lucide-react";
import { useUserStore } from "@/store/useUserStore";

// ── Step data ─────────────────────────────────────────────────────────────────

const GOALS = [
  { value: "Academic Presentations", label: "Academic Presentations", icon: Presentation, desc: "Seminars, thesis defense, class presentations" },
  { value: "Job Interviews",         label: "Job Interviews",         icon: Briefcase,    desc: "Job applications, scholarship panels, internships" },
  { value: "Public Speaking",        label: "Public Speaking",        icon: Users,        desc: "Conferences, debates, community talks" },
  { value: "Business Communication", label: "Business Communication", icon: Target,       desc: "Meetings, pitches, client-facing conversations" },
  { value: "Daily Conversation",     label: "Daily Conversation",     icon: MessageCircle,desc: "Casual conversations, English fluency practice" },
];

const SKILL_LEVELS = [
  {
    value: "Beginner",
    label: "Beginner",
    desc: "I struggle with speaking confidence, fluency, or pronunciation",
    color: "#4D7A59",
    bg: "#EDF1EB",
  },
  {
    value: "Intermediate",
    label: "Intermediate",
    desc: "I can communicate but want to sound more polished and professional",
    color: "#9C6A28",
    bg: "#F3EEE3",
  },
  {
    value: "Advanced",
    label: "Advanced",
    desc: "I speak well but want to refine specific skills (eye contact, pace, etc.)",
    color: "#9C4A40",
    bg: "#F2E7E4",
  },
] as const;

const CHALLENGES = [
  { value: "Filler Words",   icon: Mic,      color: "#23345C" },
  { value: "Pronunciation",  icon: Volume2,   color: "#5A5470" },
  { value: "Eye Contact",    icon: Eye,       color: "#4D7A59" },
  { value: "Speaking Pace",  icon: Activity,  color: "#9C6A28" },
  { value: "Confidence",     icon: Brain,     color: "#9C4A40" },
  { value: "Posture",        icon: Zap,       color: "#3C6E78" },
] as const;

const PRACTICE_TYPES = [
  { value: "Conversation",  label: "AI Conversation",        icon: MessageCircle, color: "#23345C", desc: "Everyday dialogue & fluency drills" },
  { value: "Interview",     label: "Mock Interview",          icon: Briefcase,     color: "#5A5470", desc: "Structured Q&A with AI feedback" },
  { value: "Presentation",  label: "Presentation Practice",   icon: Presentation,  color: "#9C6A28", desc: "Speeches, slides & audience simulation" },
  { value: "Pronunciation", label: "Pronunciation Training",  icon: Volume2,       color: "#4D7A59", desc: "Phoneme drills & BM-English patterns" },
] as const;

// ── Step indicator ────────────────────────────────────────────────────────────

function StepDot({ step, current, total }: { step: number; current: number; total: number }) {
  const done = step < current;
  const active = step === current;
  return (
    <div
      className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
        done
          ? "bg-[#23345C] text-white"
          : active
          ? "bg-[#23345C] text-white ring-4 ring-[#23345C]/20"
          : "bg-[#E6E2D8] text-[#9B988E]"
      }`}
    >
      {done ? <CheckCircle2 className="w-4 h-4" /> : step}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const router = useRouter();
  const { setProfile } = useUserStore();

  const [step,        setStep]        = useState(1);
  const [goal,        setGoal]        = useState("");
  const [skill,       setSkill]       = useState("");
  const [challenges,  setChallenges]  = useState<string[]>([]);
  const [practiceType,setPracticeType]= useState("");

  const TOTAL = 4;

  const toggleChallenge = (v: string) =>
    setChallenges((p) => (p.includes(v) ? p.filter((x) => x !== v) : [...p, v]));

  const canNext =
    (step === 1 && goal !== "") ||
    (step === 2 && skill !== "") ||
    (step === 3 && challenges.length > 0) ||
    (step === 4 && practiceType !== "");

  const handleFinish = () => {
    setProfile({
      id: "local",
      user_id: "local",
      age_group: "",
      communication_goal: goal,
      skill_level: skill as "Beginner" | "Intermediate" | "Advanced",
      challenges,
    });
    router.push("/dashboard");
  };

  return (
    <div className="w-full max-w-[560px] mx-auto">

      {/* ── Step indicator ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-0 mb-8">
        {Array.from({ length: TOTAL }, (_, i) => i + 1).map((s) => (
          <div key={s} className="flex items-center flex-1 last:flex-none">
            <StepDot step={s} current={step} total={TOTAL} />
            {s < TOTAL && (
              <div className={`flex-1 h-0.5 mx-1 ${s < step ? "bg-[#23345C]" : "bg-[#E6E2D8]"}`} />
            )}
          </div>
        ))}
      </div>

      {/* ── Card ───────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-3xl shadow-[0_4px_24px_rgba(0,0,0,0.10)] p-8">

        {/* ── Step 1: Goal ─────────────────────────────────────────────── */}
        {step === 1 && (
          <>
            <div className="mb-6">
              <p className="text-xs font-semibold text-[#23345C] uppercase tracking-widest mb-1">Step 1 of 4</p>
              <h1 className="font-display text-2xl text-[#17181C]">What's your main goal?</h1>
              <p className="text-sm text-[#6E6C63] mt-1">We'll personalise your practice sessions based on your answer.</p>
            </div>
            <div className="space-y-2">
              {GOALS.map(({ value, label, icon: Icon, desc }) => {
                const active = goal === value;
                return (
                  <button
                    key={value}
                    onClick={() => setGoal(value)}
                    className={`w-full flex items-center gap-4 p-4 rounded-2xl border text-left transition-all ${
                      active ? "border-[#23345C] bg-[#E8E9EF]" : "border-[#E6E2D8] hover:bg-[#F5F2EB]"
                    }`}
                  >
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${active ? "bg-[#23345C]" : "bg-[#F5F2EB]"}`}>
                      <Icon className={`w-5 h-5 ${active ? "text-white" : "text-[#6E6C63]"}`} />
                    </div>
                    <div>
                      <p className={`text-sm font-semibold ${active ? "text-[#23345C]" : "text-[#17181C]"}`}>{label}</p>
                      <p className="text-xs text-[#6E6C63] mt-0.5">{desc}</p>
                    </div>
                    {active && <CheckCircle2 className="w-5 h-5 text-[#23345C] ml-auto flex-shrink-0" />}
                  </button>
                );
              })}
            </div>
          </>
        )}

        {/* ── Step 2: Skill Level ──────────────────────────────────────── */}
        {step === 2 && (
          <>
            <div className="mb-6">
              <p className="text-xs font-semibold text-[#23345C] uppercase tracking-widest mb-1">Step 2 of 4</p>
              <h1 className="font-display text-2xl text-[#17181C]">How would you rate your speaking?</h1>
              <p className="text-sm text-[#6E6C63] mt-1">Be honest — we'll calibrate feedback difficulty to your level.</p>
            </div>
            <div className="space-y-3">
              {SKILL_LEVELS.map(({ value, label, desc, color, bg }) => {
                const active = skill === value;
                return (
                  <button
                    key={value}
                    onClick={() => setSkill(value)}
                    className={`w-full flex items-center gap-4 p-5 rounded-2xl border text-left transition-all ${
                      active ? "border-transparent" : "border-[#E6E2D8] hover:bg-[#F5F2EB]"
                    }`}
                    style={active ? { backgroundColor: bg, borderColor: color } : {}}
                  >
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 text-sm font-bold"
                      style={{ backgroundColor: active ? color : "#F1EEE6", color: active ? "#fff" : "#9B988E" }}
                    >
                      {value[0]}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-bold" style={{ color: active ? color : "#17181C" }}>{label}</p>
                      <p className="text-xs text-[#6E6C63] mt-0.5">{desc}</p>
                    </div>
                    {active && <CheckCircle2 className="w-5 h-5 flex-shrink-0" style={{ color }} />}
                  </button>
                );
              })}
            </div>
          </>
        )}

        {/* ── Step 3: Challenges ───────────────────────────────────────── */}
        {step === 3 && (
          <>
            <div className="mb-6">
              <p className="text-xs font-semibold text-[#23345C] uppercase tracking-widest mb-1">Step 3 of 4</p>
              <h1 className="font-display text-2xl text-[#17181C]">What are your main challenges?</h1>
              <p className="text-sm text-[#6E6C63] mt-1">Select all that apply. We'll focus extra coaching here.</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {CHALLENGES.map(({ value, icon: Icon, color }) => {
                const active = challenges.includes(value);
                return (
                  <button
                    key={value}
                    onClick={() => toggleChallenge(value)}
                    className={`flex items-center gap-3 p-4 rounded-2xl border text-left transition-all ${
                      active ? "border-transparent" : "border-[#E6E2D8] hover:bg-[#F5F2EB]"
                    }`}
                    style={active ? { backgroundColor: `${color}12`, borderColor: color } : {}}
                  >
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: active ? color : "#F1EEE6" }}
                    >
                      <Icon className="w-4 h-4" style={{ color: active ? "#fff" : "#9B988E" }} />
                    </div>
                    <span className="text-sm font-semibold" style={{ color: active ? color : "#17181C" }}>{value}</span>
                    {active && (
                      <CheckCircle2 className="w-4 h-4 flex-shrink-0 ml-auto" style={{ color }} />
                    )}
                  </button>
                );
              })}
            </div>
          </>
        )}

        {/* ── Step 4: Preferred Practice Type ─────────────────────────── */}
        {step === 4 && (
          <>
            <div className="mb-6">
              <p className="text-xs font-semibold text-[#23345C] uppercase tracking-widest mb-1">Step 4 of 4</p>
              <h1 className="font-display text-2xl text-[#17181C]">Preferred practice style?</h1>
              <p className="text-sm text-[#6E6C63] mt-1">Don't worry — you can use all modes anytime.</p>
            </div>
            <div className="space-y-2">
              {PRACTICE_TYPES.map(({ value, label, icon: Icon, color, desc }) => {
                const active = practiceType === value;
                return (
                  <button
                    key={value}
                    onClick={() => setPracticeType(value)}
                    className={`w-full flex items-center gap-4 p-4 rounded-2xl border text-left transition-all ${
                      active ? "border-transparent" : "border-[#E6E2D8] hover:bg-[#F5F2EB]"
                    }`}
                    style={active ? { backgroundColor: `${color}10`, borderColor: color } : {}}
                  >
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: active ? color : "#F5F2EB" }}
                    >
                      <Icon className="w-5 h-5" style={{ color: active ? "#fff" : "#6E6C63" }} />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold" style={{ color: active ? color : "#17181C" }}>{label}</p>
                      <p className="text-xs text-[#6E6C63] mt-0.5">{desc}</p>
                    </div>
                    {active && <CheckCircle2 className="w-5 h-5 flex-shrink-0" style={{ color }} />}
                  </button>
                );
              })}
            </div>
          </>
        )}

        {/* ── Navigation ─────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between mt-8 pt-6 border-t border-[#F1EEE6]">
          {step > 1 ? (
            <button
              onClick={() => setStep((s) => s - 1)}
              className="flex items-center gap-1.5 text-sm text-[#6E6C63] hover:text-[#17181C] px-4 py-2 rounded-xl hover:bg-[#F5F2EB] transition-colors"
            >
              <ChevronLeft className="w-4 h-4" /> Back
            </button>
          ) : (
            <div />
          )}

          {step < TOTAL ? (
            <button
              disabled={!canNext}
              onClick={() => setStep((s) => s + 1)}
              className="flex items-center gap-1.5 bg-[#23345C] hover:bg-[#17233E] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold px-6 py-2.5 rounded-xl transition-all press-effect"
            >
              Continue <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              disabled={!canNext}
              onClick={handleFinish}
              className="flex items-center gap-2 bg-[#23345C] hover:bg-[#17233E] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold px-6 py-2.5 rounded-xl transition-all"
            >
              <CheckCircle2 className="w-4 h-4" /> Start Practicing!
            </button>
          )}
        </div>
      </div>

      {/* ── Skip link ──────────────────────────────────────────────────── */}
      <p className="text-center mt-4 text-xs text-[#9B988E]">
        <button
          onClick={() => router.push("/dashboard")}
          className="hover:text-[#6E6C63] underline underline-offset-2 transition-colors"
        >
          Skip for now
        </button>
      </p>
    </div>
  );
}
