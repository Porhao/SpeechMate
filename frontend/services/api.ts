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

// Access tokens are short-lived: on a 401, swap the refresh token for a new
// pair once and retry the request.
async function refreshTokens(): Promise<boolean> {
  const refresh_token = localStorage.getItem("refresh_token");
  if (!refresh_token) return false;
  const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token }),
  }).catch(() => null);
  if (!res?.ok) return false;
  const tokens = await res.json();
  localStorage.setItem("access_token", tokens.access_token);
  localStorage.setItem("refresh_token", tokens.refresh_token);
  return true;
}

async function request<T>(path: string, options: RequestInit = {}, retried = false): Promise<T> {
  const isForm = options.body instanceof FormData;
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
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
