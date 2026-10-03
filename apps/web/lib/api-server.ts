/**
 * Server-side API client.
 *
 * Only server code (Server Components, route handlers) may use this. It attaches
 * the access token from the httpOnly cookie and talks to Django directly, so the
 * browser never sees the API host or a token.
 */
import { getAccessToken } from "@/lib/session";
import type { ApiError } from "@/lib/types";

export const API_BASE_URL = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export class ApiRequestError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export interface FetchOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  /** Override the bearer token (used by the refresh flow). */
  token?: string;
  /** Pass a FormData body straight through (document upload). */
  formData?: FormData;
  cache?: RequestCache;
  requestId?: string;
}

export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const token = options.token ?? (await getAccessToken());
  const headers: Record<string, string> = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.requestId) headers["X-Request-Id"] = options.requestId;

  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
    cache: options.cache ?? "no-store",
  });

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const payload = text ? safeJson(text) : {};

  if (!response.ok) {
    const error = (payload as ApiError).error;
    throw new ApiRequestError(
      response.status,
      error?.code ?? "error",
      error?.message ?? `Request failed with status ${response.status}.`,
      (error?.details as Record<string, unknown>) ?? {},
    );
  }
  return payload as T;
}

/** Like apiFetch but returns `null` instead of throwing on 404/403. */
export async function apiFetchOptional<T>(path: string, options: FetchOptions = {}): Promise<T | null> {
  try {
    return await apiFetch<T>(path, options);
  } catch (error) {
    if (error instanceof ApiRequestError && [403, 404].includes(error.status)) return null;
    throw error;
  }
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}
