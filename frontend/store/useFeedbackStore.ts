import { create } from "zustand";
import type { LiveFeedback, SpeechAnalysis, VisionAnalysis, AIFeedback, FullAnalysisResult, GazeTunnelingResult } from "@/types";

interface FeedbackState {
  liveFeedback: LiveFeedback;
  speechAnalysis: SpeechAnalysis | null;
  visionAnalysis: VisionAnalysis | null;
  aiFeedback: AIFeedback | null;
  transcript: string;
  // Full structured result from POST /analysis/run — richer than the
  // individual speech/vision/aiFeedback fields above (transcript, accent
  // detection, real recommendations, filler/stuttering breakdowns, etc.)
  fullAnalysis: FullAnalysisResult | null;
  // Computed client-side at session end from the live gaze + disfluency
  // samples collected during the session — see computeGazeTunneling.
  gazeTunneling: GazeTunnelingResult | null;
  updateLiveFeedback: (data: Partial<LiveFeedback>) => void;
  setSpeechAnalysis: (data: SpeechAnalysis) => void;
  setVisionAnalysis: (data: VisionAnalysis) => void;
  setAIFeedback: (data: AIFeedback) => void;
  setFullAnalysis: (data: FullAnalysisResult) => void;
  setGazeTunneling: (data: GazeTunnelingResult) => void;
  appendTranscript: (text: string) => void;
  reset: () => void;
}

const defaultLive: LiveFeedback = {
  fluency: 0,
  pronunciation: 0,
  eye_contact: 0,
  confidence: 0,
  speaking_pace: 0,
  posture: 0,
};

export const useFeedbackStore = create<FeedbackState>((set) => ({
  liveFeedback: defaultLive,
  speechAnalysis: null,
  visionAnalysis: null,
  aiFeedback: null,
  transcript: "",
  fullAnalysis: null,
  gazeTunneling: null,

  updateLiveFeedback: (data) =>
    set((s) => ({ liveFeedback: { ...s.liveFeedback, ...data } })),
  setSpeechAnalysis: (data) => set({ speechAnalysis: data }),
  setVisionAnalysis: (data) => set({ visionAnalysis: data }),
  setAIFeedback: (data) => set({ aiFeedback: data }),
  setFullAnalysis: (data) => set({ fullAnalysis: data }),
  setGazeTunneling: (data) => set({ gazeTunneling: data }),
  appendTranscript: (text) =>
    set((s) => ({ transcript: s.transcript + (s.transcript ? " " : "") + text })),
  reset: () =>
    set({
      liveFeedback: defaultLive, speechAnalysis: null, visionAnalysis: null,
      aiFeedback: null, transcript: "", fullAnalysis: null, gazeTunneling: null,
    }),
}));
