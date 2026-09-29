import { api } from "./api";
import { blobFilename } from "./presentation";
import type { FullAnalysisResult, LiveSession, SessionType } from "@/types";

const POLL_MS = 2500;
// Local models can take a while on CPU for long recordings
const ANALYSIS_TIMEOUT_MS = 10 * 60 * 1000;

// Live practice sessions (camera + mic with the AI partner). Requires sign-in.
export const liveService = {
  start: (session_type: SessionType) => api.post<LiveSession>("/live", { session_type }),

  end: (id: string, durationSec: number) =>
    api.post<LiveSession>(`/live/${id}/end`, { duration_sec: durationSec }),

  uploadRecording: (id: string, blob: Blob) => {
    const form = new FormData();
    form.append("file", blob, blobFilename(blob, "recording"));
    return api.upload<LiveSession>(`/live/${id}/recording`, form);
  },

  get: (id: string) => api.get<LiveSession>(`/live/${id}`),
  history: () => api.get<LiveSession[]>("/live"),
  remove: (id: string) => api.delete<void>(`/live/${id}`),

  /** Start the multimodal analysis and wait for the result. */
  analyze: async (id: string): Promise<FullAnalysisResult> => {
    await api.post<LiveSession>(`/live/${id}/analyze`, {});
    const deadline = Date.now() + ANALYSIS_TIMEOUT_MS;
    while (Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, POLL_MS));
      const s = await liveService.get(id);
      if (s.status === "complete" && s.analysis) return { ...s.analysis, warnings: s.warnings };
      if (s.status === "failed") throw new Error(s.error_detail ?? "Analysis failed");
    }
    throw new Error("Analysis is taking too long — check the session again later.");
  },
};

// The AI partner, the general coach and TTS. They return 503 when the backend
// has no OpenAI key; callers fall back (scripted prompts, browser speech).
export const conversationService = {
  partnerReply: (messages: { role: "user" | "assistant"; content: string }[], mode: string, topic?: string) =>
    api.post<{ reply: string }>("/chat/message", { messages, mode, topic }),

  coach: (question: string, history: { role: "user" | "assistant"; content: string }[]) =>
    api.post<{ answer: string }>("/coach/chat", { question, history }),

  speak: async (text: string, voice = "nova"): Promise<Blob> => {
    const res = await api.fetch("/tts/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice }),
    });
    if (!res.ok) throw new Error(`TTS ${res.status}`);
    return res.blob();
  },
};
