// Same-origin typed fetch wrapper. In dev, Vite proxies /api → :8000; in prod
// FastAPI serves both the SPA and /api from one origin, so no base URL is set.
// FastAPI errors come back as { detail: string } with 4xx/5xx — surface that
// message via ApiError so the UI can show real validation/404 text.
//
// Every request has a timeout (via AbortController) so a hung call fails cleanly
// instead of spinning forever — the slow LLM endpoints (/report, /novelty) use
// SLOW_TIMEOUT_MS (H3: the backend is bounded too, via LLM_NUM_PREDICT).

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// Fast JSON endpoints; generous enough for the one-time engine warmup.
export const DEFAULT_TIMEOUT_MS = 30_000;
// LLM-backed endpoints (/report, /novelty) + markdown/pdf export.
export const SLOW_TIMEOUT_MS = 240_000;

async function withTimeout(
  path: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    return await fetch(path, { ...init, signal: ctrl.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(
        `Request timed out after ${Math.round(timeoutMs / 1000)}s. The local model may be busy — please retry.`,
        0,
      );
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const res = await withTimeout(path, init, timeoutMs);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body — keep statusText */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export function apiGet<T>(path: string, timeoutMs?: number): Promise<T> {
  return request<T>(path, {}, timeoutMs);
}

export function apiPost<T>(path: string, body: unknown, timeoutMs?: number): Promise<T> {
  return request<T>(
    path,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    timeoutMs,
  );
}

export function apiDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}

// For markdown/pdf report formats the body is not JSON — return raw text.
// Uses the slow timeout since it triggers the same enrichment + LLM path.
export async function apiPostText(
  path: string,
  body: unknown,
  timeoutMs = SLOW_TIMEOUT_MS,
): Promise<string> {
  const res = await withTimeout(
    path,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    timeoutMs,
  );
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(detail, res.status);
  }
  return res.text();
}
