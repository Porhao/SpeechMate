"use client";

import { useState } from "react";
import Link from "next/link";
import { Mic2, Eye, EyeOff, TrendingUp } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const { login, loading, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login({ email, password });
  };

  return (
    <div className="w-full max-w-[900px] bg-white rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.12)] overflow-hidden flex min-h-[540px]">

      {/* ── Left: Blue branding panel ────────────────────────────────────── */}
      <div className="hidden lg:flex w-[400px] flex-shrink-0 bg-[#23345C] flex-col justify-between p-10">
        <div>
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 mb-12">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
              <Mic2 className="w-5 h-5 text-white" />
            </div>
            <span className="text-white font-bold text-xl">SpeechMate</span>
          </Link>

          <h2 className="text-white text-[28px] font-bold leading-tight mb-3">
            Become a confident communicator
          </h2>
          <p className="text-blue-200 text-sm leading-relaxed mb-10">
            AI-powered speech coaching that adapts to your unique communication style and learning goals.
          </p>

          {/* Feature bullets */}
          <div className="space-y-4">
            {[
              "Real-time fluency & pronunciation feedback",
              "Eye contact & posture analysis via camera",
              "Personalized AI coaching conversations",
              "Track your progress over weeks and months",
            ].map((f) => (
              <div key={f} className="flex items-start gap-3">
                <div className="w-5 h-5 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path d="M2 5l2.5 2.5 3.5-5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <span className="text-blue-100 text-sm">{f}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Testimonial */}
        <div className="border-t border-white/20 pt-6">
          <div className="flex items-center gap-2 mb-3">
            {[...Array(5)].map((_, i) => (
              <TrendingUp key={i} className="w-3.5 h-3.5 text-yellow-300" />
            ))}
          </div>
          <p className="text-blue-100 text-sm italic leading-relaxed">
            &ldquo;My confidence in presentations improved dramatically in just 3 weeks.&rdquo;
          </p>
          <p className="text-white text-sm font-semibold mt-2">Ahmad Farid &middot; UTP Student</p>
        </div>
      </div>

      {/* ── Right: Form area ─────────────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center p-8 lg:p-12">
        <div className="w-full max-w-[360px]">

          {/* Mobile logo */}
          <Link href="/" className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-8 h-8 bg-[#23345C] rounded-lg flex items-center justify-center">
              <Mic2 className="w-4 h-4 text-white" />
            </div>
            <span className="text-[#17181C] font-bold text-lg">SpeechMate</span>
          </Link>

          <h1 className="font-display text-2xl text-[#17181C] mb-1">Welcome back</h1>
          <p className="text-[#6E6C63] text-sm mb-8">Sign in to continue your journey</p>

          {error && (
            <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-xl mb-6 border border-red-100">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-[#17181C] mb-1.5">
                Email address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
                className="w-full px-4 py-2.5 rounded-xl border border-[#E6E2D8] bg-[#F5F2EB] text-[#17181C] text-sm outline-none focus:border-[#23345C] focus:ring-2 focus:ring-[#23345C]/10 transition-all placeholder:text-[#9B988E]"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-sm font-medium text-[#17181C]">Password</label>
                <button type="button" className="text-xs text-[#23345C] hover:underline">
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  autoComplete="current-password"
                  className="w-full px-4 py-2.5 pr-11 rounded-xl border border-[#E6E2D8] bg-[#F5F2EB] text-[#17181C] text-sm outline-none focus:border-[#23345C] focus:ring-2 focus:ring-[#23345C]/10 transition-all placeholder:text-[#9B988E]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9B988E] hover:text-[#6E6C63] transition-colors"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#23345C] hover:bg-[#17233E] disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold text-sm py-3 rounded-xl transition-colors mt-2 press-effect"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <p className="text-center text-sm text-[#6E6C63] mt-6">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-[#23345C] font-semibold hover:underline">
              Create one free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
