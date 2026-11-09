import { API_BASE_URL } from "@/constants";
import { api, ApiError } from "./api";
import type { BackendHealth, DeckListItem, DeckScript, DeckStatusResponse, ScriptStyle } from "@/types";

// Client for presentation decks (/sessions): upload, preparation status, slide images.
// All routes live under API_BASE_URL (…/api) except /health, which sits at the server root.

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

  create: (pptx: File, requirementPrompt?: string, onProgress?: (fraction: number) => void) => {
    const form = new FormData();
    form.append("pptx", pptx);
    if (requirementPrompt?.trim()) form.append("requirement_prompt", requirementPrompt.trim());
    return api.upload<{ session_id: string; status: string }>("/sessions", form, onProgress);
  },

  list: () => api.get<DeckListItem[]>("/sessions"),
  get: (id: string) => api.get<DeckStatusResponse>(`/sessions/${id}`),
  retry: (id: string) => api.post<{ session_id: string; status: string }>(`/sessions/${id}/retry`, {}),
  remove: (id: string) => api.delete<void>(`/sessions/${id}`),
  /** Write (or rewrite) the deck's practice script for a talk of `minutes`. */
  writeScript: (id: string, minutes: number, style: ScriptStyle) =>
    api.post<DeckScript>(`/sessions/${id}/script`, { minutes, style }),

  /** A slide's PNG. It needs the Bearer token, which an <img src> can't send: see SlideImage. */
  slideImage: (id: string, n: number) => api.blob(`/sessions/${id}/slides/${n}/image`),
};

export const DECK_IN_PROGRESS: ReadonlySet<string> = new Set(["queued", "processing_slides", "analyzing_content"]);
