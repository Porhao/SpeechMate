import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/types";

// The signed-in user, kept across reloads (services/api.ts `session` clears it on sign-out)
interface UserState {
  user: User | null;
  setUser: (user: User) => void;
  logout: () => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
      logout: () => set({ user: null }),
    }),
    { name: "speechmate-user" }
  )
);
