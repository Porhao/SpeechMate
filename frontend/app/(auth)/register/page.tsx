"use client";

import { useState } from "react";
import Link from "next/link";
import { Eye, EyeOff } from "lucide-react";
import AuthShell from "@/components/auth/AuthShell";
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
    "w-full px-4 py-2.5 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] text-[var(--ink)] text-sm outline-none focus:border-[var(--accent-ink)] focus:ring-2 focus:ring-[var(--accent-ink)]/10 transition-all placeholder:text-[var(--faint)]";

  return (
    <AuthShell busy={loading}>
          <h1 className="font-display text-[28px] leading-tight text-[var(--ink)] mt-6 lg:mt-0">Create your account</h1>
          <p className="text-sm text-[var(--muted)] mt-1.5 mb-6">Set up your profile to start practising.</p>

          {(error || passwordError) && (
            <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-xl mb-5 border border-red-100">
              {error ?? passwordError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Row 1: Name + Email */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-[var(--ink)] mb-1.5">Full name</label>
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
                <label className="block text-sm font-medium text-[var(--ink)] mb-1.5">Email</label>
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
                <label className="block text-sm font-medium text-[var(--ink)] mb-1.5">Password</label>
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
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--faint)] hover:text-[var(--muted)]"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--ink)] mb-1.5">
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
                <label className="block text-sm font-medium text-[var(--ink)] mb-1.5">
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
                <label className="block text-sm font-medium text-[var(--ink)] mb-1.5">
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
              className="w-full bg-[var(--accent)] hover:bg-[#0A0A0A] disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold text-sm py-3 rounded-xl transition-colors mt-2 press-effect"
            >
              {loading ? "Creating account…" : "Create account"}
            </button>
          </form>

          <p className="text-sm text-[var(--muted)] mt-6">
            Already have an account?{" "}
            <Link href="/login" className="font-semibold text-[var(--accent-ink)] hover:underline underline-offset-2">
              Sign in
            </Link>
          </p>
    </AuthShell>
  );
}
