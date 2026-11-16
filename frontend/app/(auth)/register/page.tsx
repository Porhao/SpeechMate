"use client";

import { useState } from "react";
import Link from "next/link";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import AuthShell from "@/components/auth/AuthShell";
import { useAuth } from "@/hooks/useAuth";

// Same fields as the sign-in form; goal, level and challenges are asked next, in onboarding
const inputClass =
  "w-full px-4 py-3 rounded-xl border border-[var(--line)] bg-[var(--surface)] text-[var(--ink)] text-sm outline-none " +
  "focus:border-[var(--accent-ink)] focus:ring-4 focus:ring-[var(--accent-ink)]/10 transition-all placeholder:text-[var(--faint)]";
const labelClass = "block text-sm font-medium text-[var(--ink)] mb-1.5";

export default function RegisterPage() {
  const { register, loading, error } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [form, setForm] = useState({ full_name: "", email: "", password: "", confirm_password: "" });

  const update = (field: keyof typeof form, value: string) => setForm((prev) => ({ ...prev, [field]: value }));
  const mismatch = !!form.confirm_password && form.password !== form.confirm_password;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    if (form.password.length < 8) { setPasswordError("Use at least 8 characters for your password."); return; }
    if (form.password !== form.confirm_password) { setPasswordError("The two passwords don't match."); return; }
    await register({ full_name: form.full_name.trim(), email: form.email.trim(), password: form.password });
  };

  return (
    <AuthShell>
      <h1 className="font-display text-[28px] leading-tight text-[var(--ink)]">Create your account</h1>
      <p className="text-sm text-[var(--muted)] mt-1.5 mb-8">It takes a minute. Then you can start practising.</p>

      {(passwordError || error) && (
        <div role="alert" className="text-sm px-4 py-3 rounded-xl mb-6" style={{ background: "rgba(194,52,44,0.06)", border: "1px solid rgba(194,52,44,0.22)", color: "var(--bad)" }}>
          {passwordError ?? error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="full_name" className={labelClass}>Full name</label>
          <input id="full_name" type="text" value={form.full_name} required autoComplete="name" autoFocus
            onChange={(e) => update("full_name", e.target.value)} placeholder="Your name" className={inputClass} />
        </div>

        <div>
          <label htmlFor="email" className={labelClass}>Email</label>
          <input id="email" type="email" value={form.email} required autoComplete="email"
            onChange={(e) => update("email", e.target.value)} placeholder="you@example.com" className={inputClass} />
        </div>

        <div>
          <label htmlFor="password" className={labelClass}>Password</label>
          <div className="relative">
            <input id="password" type={showPassword ? "text" : "password"} value={form.password} required minLength={8} autoComplete="new-password"
              onChange={(e) => update("password", e.target.value)} placeholder="At least 8 characters" className={`${inputClass} pr-11`} />
            <button type="button" onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[var(--faint)] hover:text-[var(--ink-2)] transition-colors"
              aria-label={showPassword ? "Hide password" : "Show password"}>
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div>
          <label htmlFor="confirm_password" className={labelClass}>Confirm password</label>
          <input id="confirm_password" type={showPassword ? "text" : "password"} value={form.confirm_password} required autoComplete="new-password"
            onChange={(e) => update("confirm_password", e.target.value)} placeholder="Type it again"
            aria-invalid={mismatch} className={inputClass} style={mismatch ? { borderColor: "var(--bad)" } : undefined} />
          {mismatch && <p className="text-xs mt-1.5" style={{ color: "var(--bad)" }}>The two passwords don&apos;t match yet.</p>}
        </div>

        <button type="submit" disabled={loading}
          className="w-full flex items-center justify-center gap-2 text-white font-semibold text-sm py-3 rounded-xl transition-colors disabled:opacity-60 disabled:cursor-not-allowed press-effect"
          style={{ background: "var(--accent)" }}>
          {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating your account…</> : "Create account"}
        </button>
      </form>

      <p className="text-sm text-[var(--muted)] mt-8">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-[var(--accent-ink)] hover:underline underline-offset-2">Sign in</Link>
      </p>
    </AuthShell>
  );
}
