import { API_BASE_URL } from "@/constants";
import { api, ApiError } from "./api";
import type {
  BackendHealth,
  CoachChatMessage,
  DeckListItem,
  DeckStatusResponse,
  NarratorVoices,
  PracticeRun,
  RecordingGranularity,
  SlideScript,
} from "@/types";

// Client for presentation coaching (PresentCoach): the Ideal Presentation Agent
// (/sessions) and the Coach Agent (/sessions/{id}/practice). All routes live
// under API_BASE_URL (…/api) except /health, which sits at the server root.

/** Filename for a recorded Blob — the backend picks the decoder from the extension. */
export function blobFilename(blob: Blob, base: string): string {
  const type = blob.type.toLowerCase();
  const ext = type.includes("mp4") ? "mp4"
    : type.includes("ogg") ? "ogg"
    : type.includes("wav") ? "wav"
    : type.includes("mpeg") ? "mp3"
    : "webm";
  return `${base}.${ext}`;
}

export const presentationService = {
  health: async (): Promise<BackendHealth> => {
    const root = API_BASE_URL.replace(/\/api\/?$/, "");
    const res = await fetch(`${root}/health`);
    if (!res.ok) throw new ApiError(res.status, "Health check failed");
    return res.json();
  },

  // ── Ideal Presentation Agent ────────────────────────────────────────────
  narratorVoices: () => api.get<NarratorVoices>("/narrator-voices"),

  create: (pptx: File, voiceSample?: File | Blob | null, requirementPrompt?: string, narratorVoice?: string) => {
    const form = new FormData();
    form.append("pptx", pptx);
    if (narratorVoice) form.append("narrator_voice", narratorVoice);
    if (voiceSample) {
      const name = voiceSample instanceof File ? voiceSample.name : blobFilename(voiceSample, "voice_sample");
      form.append("voice_sample", voiceSample, name);
    }
    if (requirementPrompt?.trim()) form.append("requirement_prompt", requirementPrompt.trim());
    return api.upload<{ session_id: string; status: string }>("/sessions", form);
  },

  list: () => api.get<DeckListItem[]>("/sessions"),
  get: (id: string) => api.get<DeckStatusResponse>(`/sessions/${id}`),
  scripts: (id: string) => api.get<{ slides: SlideScript[] }>(`/sessions/${id}/scripts`).then((r) => r.slides),
  retry: (id: string) => api.post<{ session_id: string; status: string }>(`/sessions/${id}/retry`, {}),
  remove: (id: string) => api.delete<void>(`/sessions/${id}`),

  videoUrl: (id: string) => `${API_BASE_URL}/sessions/${id}/video`,
  slideImageUrl: (id: string, n: number) => `${API_BASE_URL}/sessions/${id}/slides/${n}/image`,
  slideAudioUrl: (id: string, n: number) => `${API_BASE_URL}/sessions/${id}/slides/${n}/audio`,

  // ── Coach Agent ─────────────────────────────────────────────────────────
  submitPractice: (
    id: string,
    recording: File | Blob,
    granularity: RecordingGranularity = "whole_deck",
    slideIndex?: number,
  ) => {
    const form = new FormData();
    const name = recording instanceof File ? recording.name : blobFilename(recording, "practice");
    form.append("audio", recording, name);
    form.append("recording_granularity", granularity);
    if (granularity === "per_slide" && slideIndex != null) form.append("slide_index", String(slideIndex));
    return api.upload<{ practice_id: string; status: string }>(`/sessions/${id}/practice`, form);
  },

  listPractice: (id: string) => api.get<PracticeRun[]>(`/sessions/${id}/practice`),
  getPractice: (id: string, pid: string) => api.get<PracticeRun>(`/sessions/${id}/practice/${pid}`),
  chatHistory: (id: string, pid: string) =>
    api.get<{ messages: CoachChatMessage[] }>(`/sessions/${id}/practice/${pid}/chat`).then((r) => r.messages),
  chat: (id: string, pid: string, message: string) =>
    api.post<CoachChatMessage>(`/sessions/${id}/practice/${pid}/chat`, { message }),
};

export const DECK_IN_PROGRESS: ReadonlySet<string> = new Set([
  "queued", "processing_slides", "analyzing_content", "generating_scripts", "synthesizing_audio", "assembling_video",
]);
export const PRACTICE_IN_PROGRESS: ReadonlySet<string> = new Set(["queued", "transcribing", "analyzing"]);
