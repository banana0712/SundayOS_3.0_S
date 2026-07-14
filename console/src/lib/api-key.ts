/**
 * Auth token management for the Console client.
 *
 * Uses "sunday.token" for user login (new auth system, ADR-013).
 * Falls back to "sunday.key" for backward compatibility.
 *
 * When served from the same origin as the backend (via FastAPI at /console),
 * all /api/* calls go directly to the backend.
 */
"use client";

const TOKEN_KEY = "sunday.token";
const LEGACY_KEY = "sunday.key";

let _token: string | null = null;

export function getToken(): string {
  if (_token) return _token;
  if (typeof window !== "undefined") {
    _token = window.localStorage.getItem(TOKEN_KEY)
          || window.localStorage.getItem(LEGACY_KEY)
          || "";
  }
  return _token || "";
}

export function setToken(token: string): void {
  _token = token;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(TOKEN_KEY, token);
  }
}

export function clearToken(): void {
  _token = null;
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(LEGACY_KEY);
  }
}

// Deprecated aliases for backward compat
export const getApiKey = getToken;
export const setApiKey = setToken;

export function ensureApiKey(): string {
  return getToken();
}

/**
 * Authenticated fetch — adds X-Sunday-Token header automatically.
 * Use this instead of raw fetch() for all backend API calls.
 */
export async function apiFetch(
  url: string,
  options?: RequestInit,
): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string> || {}),
  };
  if (token) {
    headers["X-Sunday-Token"] = token;
  }
  if (!headers["Content-Type"] && (options?.method || "GET") !== "GET") {
    headers["Content-Type"] = "application/json";
  }
  return fetch(url, { ...options, headers });
}
