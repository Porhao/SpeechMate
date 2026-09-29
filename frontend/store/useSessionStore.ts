import { create } from "zustand";
import type { LiveSession, SessionType } from "@/types";

interface SessionState {
  activeSession: LiveSession | null;
  sessionType: SessionType | null;
  isRecording: boolean;
  isCameraOn: boolean;
  duration: number;
  startSession: (session: LiveSession, type: SessionType) => void;
  endSession: () => void;
  setRecording: (v: boolean) => void;
  setCameraOn: (v: boolean) => void;
  incrementDuration: () => void;
  resetDuration: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  activeSession: null,
  sessionType: null,
  isRecording: false,
  isCameraOn: true,
  duration: 0,

  startSession: (session, type) =>
    set({ activeSession: session, sessionType: type, duration: 0 }),
  endSession: () =>
    set({ activeSession: null, sessionType: null, isRecording: false }),
  setRecording: (v) => set({ isRecording: v }),
  setCameraOn: (v) => set({ isCameraOn: v }),
  incrementDuration: () => set((s) => ({ duration: s.duration + 1 })),
  resetDuration: () => set({ duration: 0 }),
}));
