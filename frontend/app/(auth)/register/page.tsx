"use client";

import { useState } from "react";
import Link from "next/link";
import { Mic2, Eye, EyeOff, CheckCircle } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

const LANGUAGE_OPTIONS = [
  { value: "English", label: "English" },
  { value: "Bahasa Malaysia", label: "Bahasa Malaysia" },
  { value: "Bilingual (EN + BM)", label: "Bilingual (EN + BM)" },
];

const GOAL_OPTIONS = [
  { value: "Public Speaking", label: "Public Speaking" },
  { value: "Job Interview", label: "Job Interview Preparation" },
  { value: "Daily Conversation", label: "Daily Conversation" },
  { value: "Presentation", label: "Academic / Work Presentations" },
  { value: "Pronunciation", label: "Pronunciation Improvement" },
];

export default function RegisterPage() {
  const { register, loading, error } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    confirm_password: "",
    language: "English",
    communication_goal: "Public Speaking",
  });

  const update = (field: string, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    if (form.password !== form.confirm_password) {
      setPasswordError("Passwords do not match");
      return;
    }
    if (form.password.length < 8) {
      setPasswordError("Password must be at least 8 characters");
      return;
    }
    await register({
      full_name: form.full_name,
      email: form.email,
      password: form.password,
      language: form.language,
      communication_goal: form.communication_goal,
    });
  };

  const inputClass =
    "w-full px-4 py-2.5 rounded-xl border border-[#E6E2D8] bg-[#F5F2EB] text-[#17181C] text-sm outline-none focus:border-[#23345C] focus:ring-2 focus:ring-[#23345C]/10 transition-all placeholder:text-[#9B988E]";

  return (
    <div className="w-full max-w-[960px] bg-white rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.12)] overflow-hidden flex min-h-[600px]">

      {/* ── Left: Blue panel ──────────────────────────────────────────────── */}
      <div className="hidden lg:flex w-[360px] flex-shrink-0 bg-[#23345C] flex-col justify-between p-10">
        <div>
          <Link href="/" className="flex items-center gap-3 mb-12">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
              <Mic2 className="w-5 h-5 text-white" />
            </div>
            <span className="text-white font-bold text-xl">SpeechMate</span>
          </Link>

          <h2 className="text-white text-[26px] font-bold leading-tight mb-3">
            Start your communication journey today
          </h2>
          <p className="text-blue-200 text-sm leading-relaxed mb-10">
            Join thousands of students and professionals who improved their communication with SpeechMate.
          </p>

          <div className="space-y-5">
            {[
              { step: "1", text: "Create your account" },
              { step: "2", text: "Set your communication goal" },
              { step: "3", text: "Start your first practice session" },
              { step: "4", text: "Track your progress over time" },
            ].map(({ step, text }) => (
              <div key={step} className="flex items-center gap-3">
                <div className="w-7 h-7 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-bold">{step}</span>
                </div>
                <span className="text-blue-100 text-sm">{text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="border-t border-white/20 pt-6">
          <div className="flex items-center gap-2 text-blue-100 text-xs">
            <CheckCircle className="w-4 h-4 text-green-300 flex-shrink-0" />
            Free to use &middot; No credit card required
          </div>
          <div className="flex items-center gap-2 text-blue-100 text-xs mt-2">
            <CheckCircle className="w-4 h-4 text-green-300 flex-shrink-0" />
            Supports English and Bahasa Malaysia
          </div>
        </div>
      </div>

      {/* ── Right: Form ───────────────────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center p-8 lg:p-10">
        <div className="w-full max-w-[480px]">

          {/* Mobile logo */}
          <Link href="/" className="flex items-center gap-2 mb-6 lg:hidden">
            <div className="w-8 h-8 bg-[#23345C] rounded-lg flex items-center justify-center">
              <Mic2 className="w-4 h-4 text-white" />
            </div>
            <span className="text-[#17181C] font-bold text-lg">SpeechMate</span>
          </Link>

          <h1 className="font-display text-2xl text-[#17181C] mb-1">Create your account</h1>
          <p className="text-[#6E6C63] text-sm mb-6">Free to start &middot; No credit card needed</p>

          {(error || passwordError) && (
            <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-xl mb-5 border border-red-100">
              {error ?? passwordError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Row 1: Name + Email */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-[#17181C] mb-1.5">Full name</label>
                <input
                  type="text"
                  value={form.full_name}
                  onChange={(e) => update("full_name", e.target.value)}
                  placeholder="Ahmad Farid"
                  required
                  autoComplete="name"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#17181C] mb-1.5">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => update("email", e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoComplete="email"
                  className={inputClass}
                />
              </div>
            </div>

            {/* Row 2: Password + Confirm Password */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-[#17181C] mb-1.5">Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={form.password}
                    onChange={(e) => update("password", e.target.value)}
                    placeholder="Min 8 characters"
                    required
                    autoComplete="new-password"
                    className={`${inputClass} pr-10`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9B988E] hover:text-[#6E6C63]"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#17181C] mb-1.5">
                  Confirm password
                </label>
                <input
                  type={showPassword ? "text" : "password"}
                  value={form.confirm_password}
                  onChange={(e) => update("confirm_password", e.target.value)}
                  placeholder="Re-enter password"
                  required
                  autoComplete="new-password"
                  className={`${inputClass} ${
                    form.confirm_password && form.password !== form.confirm_password
                      ? "border-red-300 focus:border-red-400 focus:ring-red-100"
                      : ""
                  }`}
                />
              </div>
            </div>

            {/* Row 3: Language + Goal */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-[#17181C] mb-1.5">
                  Preferred language
                </label>
                <select
                  value={form.language}
                  onChange={(e) => update("language", e.target.value)}
                  className={inputClass}
                >
                  {LANGUAGE_OPTIONS.map(({ value, label }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#17181C] mb-1.5">
                  Communication goal
                </label>
                <select
                  value={form.communication_goal}
                  onChange={(e) => update("communication_goal", e.target.value)}
                  className={inputClass}
                >
                  {GOAL_OPTIONS.map(({ value, label }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#23345C] hover:bg-[#17233E] disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold text-sm py-3 rounded-xl transition-colors mt-2 press-effect"
            >
              {loading ? "Creating account..." : "Create free account"}
            </button>
          </form>

          <p className="text-center text-sm text-[#6E6C63] mt-5">
            Already have an account?{" "}
            <Link href="/login" className="text-[#23345C] font-semibold hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
