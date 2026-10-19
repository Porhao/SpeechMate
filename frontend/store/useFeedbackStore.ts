import { create } from "zustand";

// The live transcript of the user's words during a session (the analysis itself lives on the server)
interface FeedbackState {
  transcript: string;
  appendTranscript: (text: string) => void;
  reset: () => void;
}

export const useFeedbackStore = create<FeedbackState>((set) => ({
  transcript: "",
  appendTranscript: (text) =>
    set((s) => ({ transcript: s.transcript + (s.transcript ? " " : "") + text })),
  reset: () => set({ transcript: "" }),
}));
