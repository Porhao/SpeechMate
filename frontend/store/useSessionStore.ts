import { create } from "zustand";

// The live session's recording state and timer, shared by the session page's controls
interface SessionState {
  isRecording: boolean;
  isCameraOn: boolean;
  duration: number;
  setRecording: (v: boolean) => void;
  setCameraOn: (v: boolean) => void;
  incrementDuration: () => void;
  resetDuration: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  isRecording: false,
  isCameraOn: true,
  duration: 0,

  setRecording: (v) => set({ isRecording: v }),
  setCameraOn: (v) => set({ isCameraOn: v }),
  incrementDuration: () => set((s) => ({ duration: s.duration + 1 })),
  resetDuration: () => set({ duration: 0 }),
}));
