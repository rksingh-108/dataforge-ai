/**
 * Browser-side API client.
 *
 * Everything goes through the same-origin BFF proxy (`/api/proxy/...`), which
 * attaches the access token server-side. The browser never holds a token.
 */
import type { ApiError } from "@/lib/types";

export class ClientApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "ClientApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type Method = "GET" | "POST" | "PATCH" | "DELETE";

export async function clientFetch<T>(
  path: string,
  options: { method?: Method; body?: unknown; formData?: FormData } = {},
): Promise<T> {
  const proxied = `/api/proxy${path.startsWith("/") ? path : `/${path}`}`;
  const headers: Record<string, string> = { Accept: "application/json" };
  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const response = await fetch(proxied, {
    method: options.method ?? "GET",
    headers,
    body,
  });

  if (response.status === 204) return undefined as T;
  const text = await response.text();
  const payload = text ? safeJson(text) : {};

  if (!response.ok) {
    const error = (payload as ApiError).error;
    throw new ClientApiError(
      response.status,
      error?.code ?? "error",
      error?.message ?? `Request failed with status ${response.status}.`,
      (error?.details as Record<string, unknown>) ?? {},
    );
  }
  return payload as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}
