import { API_BASE_URL } from "@/constants";

export const visionService = {
  uploadVideo: async (sessionId: string, blob: Blob): Promise<{ file_url: string }> => {
    const token = localStorage.getItem("access_token");
    const form = new FormData();
    form.append("file", blob, "recording.webm");
    form.append("session_id", sessionId);

    const res = await fetch(`${API_BASE_URL}/vision/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    return res.json();
  },
};
