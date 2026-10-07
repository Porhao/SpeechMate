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
  const { setUser, setProfile, logout: storeLogout } = useUserStore();

  const login = async (data: LoginPayload) => {
    setLoading(true);
    setError(null);
    try {
      await authService.login(data);
      const user = await authService.me();
      setUser(user);
      setProfile({
        id: user.id,
        user_id: user.id,
        age_group: user.age_group ?? "",
        communication_goal: user.communication_goal ?? "",
        skill_level: (user.skill_level as "Beginner" | "Intermediate" | "Advanced") ?? "Beginner",
        challenges: user.challenges,
      });
      // Back to where sign-in was asked for; same-origin paths only (no open redirect)
      const next = new URLSearchParams(window.location.search).get("next");
      router.push(next?.startsWith("/") && !next.startsWith("//") ? next : "/home");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const register = async (data: RegisterPayload) => {
    setLoading(true);
    setError(null);
    try {
      await authService.register(data);
      router.push("/login");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    await authService.logout();
    storeLogout();
    router.push("/");
  };

  return { login, register, logout, loading, error };
}
