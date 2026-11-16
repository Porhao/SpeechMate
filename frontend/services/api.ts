import { API_BASE_URL } from "@/constants";
import { useUserStore } from "@/store/useUserStore";
import type { BackendHealth } from "@/types";

const CONSENT_REQUIRED = "cloud_consent_required";
export const CONSENT_EVENT = "speechmate:consent-required";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// ── Who is signed in: the access token (and the saved user, store/useUserStore.ts) ──
const TOKEN_KEY = "access_token";
export const session = {
  token: () => (typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null),
  start: (accessToken: string) => localStorage.setItem(TOKEN_KEY, accessToken),
  /** Forget the token and the saved user (signing out, or the session expired). */
  end: () => { localStorage.removeItem(TOKEN_KEY); useUserStore.getState().logout(); },
};

function authHeader(): Record<string, string> {
  const token = session.token();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Access tokens are short-lived (30 min): on a 401, get a new one once and retry the request.
// The refresh token is an httpOnly cookie the browser sends to /auth/* (page scripts can't read it).
async function refreshTokens(): Promise<boolean> {
  const res = await fetch(`${API_BASE_URL}/auth/refresh`, { method: "POST", credentials: "include" }).catch(() => null);
  if (!res?.ok) return false;
  session.start((await res.json()).access_token);
  return true;
}

/** The session is over (refresh token expired or gone): forget it and go to sign-in. */
function signedOut(): never {
  session.end();
  window.location.href = `/login?next=${encodeURIComponent(location.pathname + location.search)}`;
  throw new ApiError(401, "Your session has expired. Please sign in again.");
}

async function request<T>(path: string, options: RequestInit = {}, retried = false): Promise<T> {
  const isForm = options.body instanceof FormData;
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      // The refresh cookie only exists for /auth/*; everything else uses the Bearer token
      credentials: path.startsWith("/auth/") ? "include" : "same-origin",
      headers: {
        ...(isForm ? {} : { "Content-Type": "application/json" }),
        ...authHeader(),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError(0, `Can't reach the SpeechMate backend at ${API_BASE_URL}. Is it running?`);
  }

  // /auth/* 401s are answers (wrong password…), not an expired session
  if (res.status === 401 && !path.startsWith("/auth/")) {
    if (!retried && (await refreshTokens())) return request<T>(path, options, true);
    signedOut();
  }
  if (!res.ok) throw apiError(res.status, await res.json().catch(() => ({ detail: res.statusText })));
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function apiError(status: number, body: { detail?: unknown } | null): ApiError {
  const detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail ?? "");
  // The server refuses cloud processing until the user agrees: show the consent dialog (ConsentGate)
  if (status === 403 && detail === CONSENT_REQUIRED && typeof window !== "undefined") {
    window.dispatchEvent(new Event(CONSENT_EVENT));
    return new ApiError(403, "Please agree to cloud processing first, then try again.");
  }
  return new ApiError(status, detail && detail !== '""' ? detail : "Request failed");
}

/** A form upload that reports progress (0–1). fetch() can't watch an upload, so this uses XHR. */
function uploadWithProgress<T>(path: string, form: FormData, onProgress: (fraction: number) => void, retried = false): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE_URL}${path}`);
    for (const [k, v] of Object.entries(authHeader())) xhr.setRequestHeader(k, v);
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(e.loaded / e.total); };
    xhr.onerror = () => reject(new ApiError(0, `Can't reach the SpeechMate backend at ${API_BASE_URL}. Is it running?`));
    xhr.onload = async () => {
      let body: { detail?: unknown } | null = null;
      try { body = JSON.parse(xhr.responseText); } catch { /* not JSON */ }
      if (xhr.status === 401 && !retried && (await refreshTokens())) {
        uploadWithProgress<T>(path, form, onProgress, true).then(resolve, reject);
      } else if (xhr.status === 401) {
        try { signedOut(); } catch (e) { reject(e); }
      } else if (xhr.status >= 200 && xhr.status < 300) {
        resolve(body as T);
      } else {
        reject(apiError(xhr.status, body ?? { detail: xhr.statusText }));
      }
    };
    xhr.send(form);
  });
}

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

export const api = {
  /** What the server can do (speech recognition, LLM…). /health sits at the server root, outside /api. */
  health: async (): Promise<BackendHealth> => {
    const res = await fetch(`${API_BASE_URL.replace(/\/api\/?$/, "")}/health`);
    if (!res.ok) throw new ApiError(res.status, "Health check failed");
    return res.json();
  },
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "DELETE", ...(body !== undefined ? { body: JSON.stringify(body) } : {}) }),
  upload: <T>(path: string, form: FormData, onProgress?: (fraction: number) => void) =>
    onProgress ? uploadWithProgress<T>(path, form, onProgress) : request<T>(path, { method: "POST", body: form }),
  /** Raw fetch to the API (for binary responses such as TTS audio). */
  fetch: (path: string, init: RequestInit = {}) =>
    fetch(`${API_BASE_URL}${path}`, { ...init, headers: { ...authHeader(), ...init.headers } }),
  /** A signed-in binary download (e.g. a slide image), refreshing the token once on 401. */
  blob: async (path: string): Promise<Blob> => {
    let res = await api.fetch(path);
    if (res.status === 401 && (await refreshTokens())) res = await api.fetch(path);
    if (res.status === 401) signedOut();
    if (!res.ok) throw new ApiError(res.status, res.statusText || "Request failed");
    return res.blob();
  },
};
