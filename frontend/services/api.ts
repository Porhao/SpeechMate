import { API_BASE_URL } from "@/constants";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function authHeader(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Access tokens are short-lived (30 min): on a 401, get a new one once and retry the request.
// The refresh token is an httpOnly cookie the browser sends to /auth/* (page scripts can't
// read it). A refresh token left in localStorage by an older version is used once, then deleted.
async function refreshTokens(): Promise<boolean> {
  const legacy = localStorage.getItem("refresh_token");
  const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    ...(legacy ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: legacy }) } : {}),
  }).catch(() => null);
  localStorage.removeItem("refresh_token");
  if (!res?.ok) return false;
  localStorage.setItem("access_token", (await res.json()).access_token);
  return true;
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

  if (res.status === 401 && !retried && path !== "/auth/refresh" && (await refreshTokens())) {
    return request<T>(path, options, true);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    throw new ApiError(res.status, detail || "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
  /** Raw fetch to the API (for binary responses such as TTS audio). */
  fetch: (path: string, init: RequestInit = {}) =>
    fetch(`${API_BASE_URL}${path}`, { ...init, headers: { ...authHeader(), ...init.headers } }),
};
