import { api, ApiError, session } from "./api";
import type { AuthTokens, User, UserProfileUpdate } from "@/types";

// Token refresh happens automatically in api.ts when a request gets a 401.

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
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
    session.start(tokens.access_token);
    return tokens;
  },

  logout: () => {
    session.end();
    return api.post("/auth/logout", {}).catch(() => null);  // clears the refresh cookie; signing out locally must still happen
  },

  me: () => api.get<User>("/users/profile"),

  updateProfile: (data: UserProfileUpdate) => api.put<User>("/users/profile", data),

  /** Agree to (or withdraw from) cloud processing: audio to Groq, text to Gemini. */
  setConsent: (accept: boolean) => api.post<User>("/users/me/consent", { accept }),

  /** Download everything stored about the user as one JSON file. */
  exportData: async () => {
    const url = URL.createObjectURL(await api.blob("/users/me/export"));
    const a = Object.assign(document.createElement("a"), { href: url, download: "speechmate-my-data.json" });
    a.click();
    URL.revokeObjectURL(url);
  },

  /** Delete the account and all its data; the password is asked again. */
  deleteAccount: (password: string) =>
    api.delete("/users/me", { password }).catch((e) => {
      throw e instanceof ApiError && e.status === 403 ? new Error("Wrong password") : e;
    }),

  isSignedIn: () => !!session.token(),
};
