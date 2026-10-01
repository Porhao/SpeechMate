"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Eye, EyeOff, Loader2 } from "lucide-react";
import AuthShell, { useOrbPulse } from "@/components/auth/AuthShell";
import { useAuth } from "@/hooks/useAuth";
import { authService } from "@/services/auth";

// The seeded local test account (backend/scripts/seed_demo.py, SEED_DEMO_DATA=true).
// Hide the shortcut with NEXT_PUBLIC_SHOW_DEMO_LOGIN=false.
const DEMO = { email: "demo@speechmate.dev", password: "Demo1234!" };
const SHOW_DEMO = process.env.NEXT_PUBLIC_SHOW_DEMO_LOGIN !== "false";

const inputClass =
  "w-full px-4 py-3 rounded-xl border border-[var(--line)] bg-[var(--surface)] text-[var(--ink)] text-sm outline-none " +
  "focus:border-[#23345C] focus:ring-4 focus:ring-[#23345C]/10 transition-all placeholder:text-[var(--faint)]";

function LoginForm({ onBusy }: { onBusy: (busy: boolean) => void }) {
  const { login, loading, error } = useAuth();
  const pulse = useOrbPulse();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => { onBusy(loading); }, [loading, onBusy]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login({ email: email.trim(), password });
  };

  return (
    <>
      <h1 className="font-display text-[28px] leading-tight text-[var(--ink)] mt-6 lg:mt-0">Sign in</h1>
      <p className="text-sm text-[var(--muted)] mt-1.5 mb-8">Welcome back. Pick up your practice where you left off.</p>

      {error && (
        <div role="alert" className="text-sm px-4 py-3 rounded-xl mb-6" style={{ background: "rgba(140,59,50,0.06)", border: "1px solid rgba(140,59,50,0.22)", color: "var(--bad)" }}>
          {error}
        </div>
      )}

      <form onSubmit={submit} className="space-y-5">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-[var(--ink)] mb-1.5">Email</label>
          <input
            id="email" type="email" value={email} required autoComplete="email" autoFocus
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com" className={inputClass}
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-[var(--ink)] mb-1.5">Password</label>
          <div className="relative">
            <input
              id="password" type={showPassword ? "text" : "password"} value={password} required autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password" className={`${inputClass} pr-11`}
            />
            <button
              type="button" onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[var(--faint)] hover:text-[var(--ink-2)] transition-colors"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <button
          type="submit" disabled={loading}
          className="w-full flex items-center justify-center gap-2 text-white font-semibold text-sm py-3 rounded-xl transition-colors disabled:opacity-60 disabled:cursor-not-allowed press-effect"
          style={{ background: "var(--accent)" }}
        >
          {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Signing in…</> : <>Sign in <ArrowRight className="w-4 h-4" /></>}
        </button>
      </form>

      {SHOW_DEMO && (
        <div className="mt-6 rounded-xl px-4 py-3 flex items-center justify-between gap-3" style={{ background: "var(--surface-2)", border: "1px dashed var(--line-strong)" }}>
          <p className="text-xs text-[var(--muted)] leading-relaxed">
            Testing locally? Use the demo account<br />
            <span className="font-mono text-[11px] text-[var(--ink-2)]">{DEMO.email}</span>
          </p>
          <button
            type="button"
            onClick={() => { setEmail(DEMO.email); setPassword(DEMO.password); pulse(); }}
            className="flex-shrink-0 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
            style={{ color: "var(--accent-ink)", border: "1px solid #23345C33", background: "var(--surface)" }}
          >
            Fill in
          </button>
        </div>
      )}

      <p className="text-sm text-[var(--muted)] mt-8">
        New to SpeechMate?{" "}
        <Link href="/register" className="font-semibold text-[var(--accent-ink)] hover:underline underline-offset-2">Create an account</Link>
      </p>
    </>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  // Already signed in: go straight into the app
  useEffect(() => {
    if (authService.isSignedIn()) router.replace("/home");
  }, [router]);

  return (
    <AuthShell busy={busy}>
      <LoginForm onBusy={setBusy} />
    </AuthShell>
  );
}
