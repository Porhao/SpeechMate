import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, UserProfile } from "@/types";

interface UserState {
  user: User | null;
  profile: UserProfile | null;
  isAuthenticated: boolean;
  setUser: (user: User) => void;
  setProfile: (profile: UserProfile) => void;
  logout: () => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      user: null,
      profile: null,
      isAuthenticated: false,

      setUser: (user) => set({ user, isAuthenticated: true }),
      setProfile: (profile) => set({ profile }),
      logout: () => set({ user: null, profile: null, isAuthenticated: false }),
    }),
    { name: "speechmate-user" }
  )
);
