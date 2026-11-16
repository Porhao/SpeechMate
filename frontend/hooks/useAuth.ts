"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { authService } from "@/services/auth";
import { useUserStore } from "@/store/useUserStore";
import type { LoginPayload, RegisterPayload } from "@/services/auth";

export function useAuth() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const setUser = useUserStore((s) => s.setUser);

  const signIn = async (data: LoginPayload) => {
    await authService.login(data);
    setUser(await authService.me());
  };

  const login = async (data: LoginPayload) => {
    setLoading(true);
    setError(null);
    try {
      await signIn(data);
      // Back to where sign-in was asked for; same-origin paths only (no open redirect)
      const next = new URLSearchParams(window.location.search).get("next");
      router.push(next?.startsWith("/") && !next.startsWith("//") ? next : "/home");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  // A new account is signed in straight away and asked for its goal, level and challenges
  const register = async (data: RegisterPayload) => {
    setLoading(true);
    setError(null);
    try {
      await authService.register(data);
      await signIn({ email: data.email, password: data.password });
      router.push("/onboarding");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    await authService.logout();
    router.push("/");
  };

  return { login, register, logout, loading, error };
}

/** For actions that need an account: true when signed in, else off to sign-in (coming back to `next`). */
export function requireSignIn(router: ReturnType<typeof useRouter>, next = location.pathname + location.search): boolean {
  if (authService.isSignedIn()) return true;
  router.push(`/login?next=${encodeURIComponent(next)}`);
  return false;
}
