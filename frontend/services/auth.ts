import { api } from "./api";
import type { AuthTokens, User, UserProfileUpdate } from "@/types";

// Token refresh happens automatically in api.ts when a request gets a 401.

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
  language: string;
  communication_goal: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export const authService = {
  register: (data: RegisterPayload) =>
    api.post<{ message: string }>("/auth/register", data),

  login: async (data: LoginPayload): Promise<AuthTokens> => {
    const tokens = await api.post<AuthTokens>("/auth/login", data);
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    return tokens;
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    return api.post("/auth/logout", {}).catch(() => null);
  },

  me: () => api.get<User>("/users/profile"),

  updateProfile: (data: UserProfileUpdate) => api.put<User>("/users/profile", data),

  isSignedIn: () => typeof window !== "undefined" && !!localStorage.getItem("access_token"),
};
