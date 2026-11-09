import { api } from "./api";
import type { AuthTokens, User, UserProfileUpdate } from "@/types";

// Token refresh happens automatically in api.ts when a request gets a 401.

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
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
    const tokens = await api.post<AuthTokens>("/auth/login", data);  // also sets the httpOnly refresh cookie
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.removeItem("refresh_token");  // left over from versions before the cookie
    return tokens;
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    return api.post("/auth/logout", {}).catch(() => null);  // clears the refresh cookie
  },

  me: () => api.get<User>("/users/profile"),

  updateProfile: (data: UserProfileUpdate) => api.put<User>("/users/profile", data),

  /** Agree to (or withdraw from) cloud processing: audio to Groq, text to Gemini. */
  setConsent: (accept: boolean) => api.post<User>("/users/me/consent", { accept }),

  /** Download everything stored about the user as one JSON file. */
  exportData: async () => {
    const res = await api.fetch("/users/me/export");
    if (!res.ok) throw new Error(`Export failed (${res.status})`);
    const url = URL.createObjectURL(await res.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: "speechmate-my-data.json" });
    a.click();
    URL.revokeObjectURL(url);
  },

  /** Delete the account and all its data; the password is asked again. */
  deleteAccount: (password: string) =>
    api.fetch("/users/me", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) })
      .then(async (res) => {
        if (!res.ok) throw new Error(res.status === 403 ? "Wrong password" : (await res.json().catch(() => ({}))).detail ?? "Couldn't delete the account");
      }),

  isSignedIn: () => typeof window !== "undefined" && !!localStorage.getItem("access_token"),
};
