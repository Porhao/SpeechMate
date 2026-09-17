import { API_BASE_URL } from "@/constants";
import type { SpeechAnalysis } from "@/types";

export const speechService = {
  uploadAudio: async (sessionId: string, blob: Blob): Promise<{ file_url: string }> => {
    const token = localStorage.getItem("access_token");
    const form = new FormData();
    form.append("file", blob, "recording.webm");
    form.append("session_id", sessionId);

    const res = await fetch(`${API_BASE_URL}/speech/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    return res.json();
  },

  analyze: async (sessionId: string): Promise<SpeechAnalysis> => {
    const token = localStorage.getItem("access_token");
    const res = await fetch(`${API_BASE_URL}/speech/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ session_id: sessionId }),
    });
    return res.json();
  },
};
