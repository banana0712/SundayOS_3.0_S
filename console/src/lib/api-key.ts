/**
 * API key management for the Console client.
 *
 * Reads the same localStorage key as webchat.py (sunday.key).
 * When served from the same origin as the backend (via FastAPI at /console),
 * all /api/* calls go directly to the backend.
 */
"use client";

const KEY_NAME = "sunday.key";

let _key: string | null = null;

export function getApiKey(): string {
  if (_key) return _key;
  if (typeof window !== "undefined") {
    _key = window.localStorage.getItem(KEY_NAME) || "";
  }
  return _key || "";
}

export function setApiKey(key: string): void {
  _key = key;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(KEY_NAME, key);
  }
}

export function ensureApiKey(): string {
  const existing = getApiKey();
  if (existing) return existing;
  if (typeof window !== "undefined") {
    const prompted = window.prompt(
      "Enter your Sunday API Key:"
    );
    if (prompted) {
      setApiKey(prompted.trim());
      return prompted.trim();
    }
  }
  return "";
}

/**
 * Authenticated fetch — adds X-API-Key header automatically.
 * Use this instead of raw fetch() for all backend API calls.
 */
export async function apiFetch(
  url: string,
  options?: RequestInit,
): Promise<Response> {
  const key = getApiKey();
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string> || {}),
  };
  if (key) {
    headers["X-API-Key"] = key;
  }
  if (!headers["Content-Type"] && (options?.method || "GET") !== "GET") {
    headers["Content-Type"] = "application/json";
  }
  return fetch(url, { ...options, headers });
}
