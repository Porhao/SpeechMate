import { api, ApiError } from "./api";
import { blobFilename } from "./presentation";
import type { InterviewSetup, LiveSession, PracticePlan, SessionType, Turn } from "@/types";

// The AI partner's voice: Kokoro-82M running in the browser (kokoro-js), so it needs no server.
// The model downloads once (~90 MB at q8, ~300 MB fp32 on WebGPU) and the browser caches it.
const KOKORO_MODEL = "onnx-community/Kokoro-82M-v1.0-ONNX";
const KOKORO_VOICE = "af_heart";
let kokoroLoading: Promise<unknown> | null = null;
let kokoro: import("kokoro-js").KokoroTTS | null = null;

/** Starts the download once; `kokoro` is set when it's ready. A failed download is retried next time. */
function loadKokoro() {
  kokoroLoading ??= import("kokoro-js")
    .then(async ({ KokoroTTS }) => {
      // `navigator.gpu` can exist without a usable GPU (headless, blocklisted drivers): ask for an adapter
      const gpu = (navigator as Navigator & { gpu?: { requestAdapter(): Promise<unknown> } }).gpu;
      const webgpu = Boolean(await gpu?.requestAdapter().catch(() => null));
      return KokoroTTS.from_pretrained(KOKORO_MODEL, webgpu ? { device: "webgpu", dtype: "fp32" } : { device: "wasm", dtype: "q8" });
    })
    .then((tts) => { kokoro = tts; })
    .catch((e) => { kokoroLoading = null; console.warn("Browser voice could not load", e); });
}

// Live practice sessions (camera + mic with the AI partner). Requires sign-in.
export const liveService = {
  /** Conversation: just a type (and topic). Interview: the setup (+ the previewed plan).
   *  Presentation: the deck whose Q&A to rehearse. */
  start: (body: {
    session_type: SessionType; topic?: string;
    interview?: InterviewSetup; plan?: PracticePlan; deck_id?: string;
    presentation_mode?: "talk" | "qa"; use_script?: boolean;
  }) => api.post<LiveSession>("/live", body),

  end: (id: string, durationSec: number, turns: Turn[] = [], clientMetrics?: Record<string, unknown>) =>
    api.post<LiveSession>(`/live/${id}/end`, { duration_sec: durationSec, turns, client_metrics: clientMetrics }),

  uploadRecording: (id: string, blob: Blob) => {
    const form = new FormData();
    form.append("file", blob, blobFilename(blob, "recording"));
    return api.upload<LiveSession>(`/live/${id}/recording`, form);
  },

  get: (id: string) => api.get<LiveSession>(`/live/${id}`),
  /** Summaries (score, the drills, pillars, a few context labels; no turns): `get` has the rest. */
  history: (deckId?: string) => api.get<LiveSession[]>(deckId ? `/live?deck_id=${deckId}` : "/live"),
  remove: (id: string) => api.delete<void>(`/live/${id}`),

  /** Start the analysis in the background (poll `get` for the result). */
  startAnalysis: (id: string) => api.post<LiveSession>(`/live/${id}/analyze`, {}),

};

// Mock-interview preparation: read a resume, preview the curated question plan
export const interviewService = {
  readResume: (file: File, onProgress?: (fraction: number) => void) => {
    const form = new FormData();
    form.append("file", file, file.name);
    return api.upload<{ text: string; chars: number }>("/interview/resume", form, onProgress);
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

  /** Transcribe one spoken turn on the backend (cloud Whisper). 503 = not available. */
  /** `context` (the AI's last line, the role or deck…) helps the model hear topic words right. */
  transcribe: async (audio: Blob, context?: string): Promise<string> => {
    const form = new FormData();
    form.append("file", audio, "turn.wav");
    if (context) form.append("context", context.slice(-1000));
    // Retry a dropped request, a rate limit or a provider hiccup; 503 (no STT configured) and other 4xx are final
    for (let attempt = 0; ; attempt++) {
      try {
        return (await api.upload<{ text: string }>("/stt", form)).text;
      } catch (e) {
        const status = e instanceof ApiError ? e.status : 0;
        const transient = status === 0 || status === 429 || status === 502 || status === 504 || status === 500;
        if (!transient || attempt >= 2) throw e;
        await new Promise((r) => setTimeout(r, 800 * (attempt + 1)));
      }
    }
  },

  /** Start downloading the voice model early, so the first reply doesn't wait for it. */
  preloadVoice: loadKokoro,

  /** Like `speak`, one sentence at a time, so playback can start while the rest is generated.
   *  Before the browser model has loaded it yields `speak`'s single clip. */
  speakStream: async function* (text: string): AsyncGenerator<Blob> {
    loadKokoro();
    if (!kokoro) { yield await conversationService.speak(text); return; }
    let yielded = false;
    try {
      // Our own closed splitter: kokoro-js 1.2.1 never closes the one it makes for a plain string,
      // so its stream would wait forever after the last sentence
      const { TextSplitterStream } = await import("kokoro-js");
      const splitter = new TextSplitterStream();
      splitter.push(text);
      splitter.close();
      for await (const { audio } of kokoro.stream(splitter, { voice: KOKORO_VOICE })) { yielded = true; yield audio.toBlob(); }
    } catch (e) {
      if (yielded) throw e;
      yield await conversationService.speak(text);  // failed before any audio: the backend's voice
    }
  },

  /** Speech for the partner's reply: Kokoro in the browser once it has loaded, until then (or if it
   *  fails) the backend's /tts/speak; the caller falls back to the browser's built-in voice after that. */
  speak: async (text: string, voice = "nova"): Promise<Blob> => {
    loadKokoro();
    if (kokoro) {
      try {
        return (await kokoro.generate(text, { voice: KOKORO_VOICE })).toBlob();
      } catch (e) {
        console.warn("Browser voice failed, trying the backend", e);
      }
    }
    const res = await api.fetch("/tts/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice }),
    });
    if (!res.ok) throw new Error(`TTS ${res.status}`);
    return res.blob();
  },
};
