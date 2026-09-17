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
  const { setUser, logout: storeLogout } = useUserStore();

  const login = async (data: LoginPayload) => {
    setLoading(true);
    setError(null);
    try {
      await authService.login(data);
      const user = await authService.me();
      setUser(user);
      router.push("/dashboard");
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
