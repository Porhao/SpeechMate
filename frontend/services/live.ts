import { api } from "./api";
import { blobFilename } from "./presentation";
import type { FullAnalysisResult, InterviewSetup, LiveSession, PracticePlan, SessionType, Turn } from "@/types";

const POLL_MS = 2500;
// Local models can take a while on CPU for long recordings
const ANALYSIS_TIMEOUT_MS = 10 * 60 * 1000;

// Live practice sessions (camera + mic with the AI partner). Requires sign-in.
export const liveService = {
  /** Conversation: just a type (and topic). Interview: the setup (+ the previewed plan).
   *  Presentation: the deck whose Q&A to rehearse. */
  start: (body: {
    session_type: SessionType; topic?: string;
    interview?: InterviewSetup; plan?: PracticePlan; deck_id?: string;
  }) => api.post<LiveSession>("/live", body),

  end: (id: string, durationSec: number, turns: Turn[] = [], clientMetrics?: Record<string, unknown>) =>
    api.post<LiveSession>(`/live/${id}/end`, { duration_sec: durationSec, turns, client_metrics: clientMetrics }),

  uploadRecording: (id: string, blob: Blob) => {
    const form = new FormData();
    form.append("file", blob, blobFilename(blob, "recording"));
    return api.upload<LiveSession>(`/live/${id}/recording`, form);
  },

  get: (id: string) => api.get<LiveSession>(`/live/${id}`),
  history: () => api.get<LiveSession[]>("/live"),
  remove: (id: string) => api.delete<void>(`/live/${id}`),

  /** Start the analysis in the background (poll `get` for the result). */
  startAnalysis: (id: string) => api.post<LiveSession>(`/live/${id}/analyze`, {}),

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

// Mock-interview preparation: read a resume, preview the curated question plan
export const interviewService = {
  readResume: (file: File) => {
    const form = new FormData();
    form.append("file", file, file.name);
    return api.upload<{ text: string; chars: number }>("/interview/resume", form);
  },
  plan: (setup: InterviewSetup) => api.post<PracticePlan>("/interview/plan", setup),
};

// The AI partner and its voice. They return 503 when the backend
// has no OpenAI key; callers fall back (scripted prompts, browser speech).
export const conversationService = {
  /** With `liveId` of an Interview / Q&A session the partner follows its question plan. */
  partnerReply: (messages: { role: "user" | "assistant"; content: string }[], mode: string, topic?: string, liveId?: string) =>
    api.post<{ reply: string; progress?: { asked: number; followups: number }; total_questions?: number }>(
      "/chat/message", { messages, mode, topic, live_id: liveId }),

  /** Transcribe one spoken turn on the backend (local faster-whisper). 503 = not available. */
  transcribe: async (audio: Blob): Promise<string> => {
    const form = new FormData();
    form.append("file", audio, "turn.wav");
    return (await api.upload<{ text: string }>("/stt", form)).text;
  },

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
