import { api } from "./api";
import type { DeckListItem, DeckScript, DeckStatusResponse, ScriptStyle } from "@/types";

// Client for presentation decks (/sessions): upload, preparation status, slide images.

export const presentationService = {
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

