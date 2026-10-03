/**
 * Same-origin API proxy (the "BFF" boundary).
 *
 * - attaches the access token from the httpOnly cookie,
 * - refreshes once on a 401 and retries the original request,
 * - forwards the response body and status unchanged.
 *
 * The browser only ever talks to this route, so there is no CORS surface and no
 * token in client-side storage.
 */
import { NextResponse } from "next/server";

import { API_BASE_URL } from "@/lib/api-server";
import { getAccessToken, getRefreshToken, setAccessToken, clearSession } from "@/lib/session";

const FORWARDED_METHODS = ["GET", "POST", "PATCH", "PUT", "DELETE"] as const;
type ForwardedMethod = (typeof FORWARDED_METHODS)[number];

async function handle(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const url = new URL(request.url);
  const target = `${API_BASE_URL}/${path.join("/")}${url.search}`;

  const method = request.method.toUpperCase() as ForwardedMethod;
  if (!FORWARDED_METHODS.includes(method)) {
    return NextResponse.json(
      { error: { code: "method_not_allowed", message: "Method not allowed." } },
      { status: 405 },
    );
  }

  const body = method === "GET" || method === "DELETE" ? undefined : await request.arrayBuffer();
  const contentType = request.headers.get("content-type") ?? "application/json";

  let response = await forward(target, method, body, contentType, await getAccessToken());

  if (response.status === 401) {
    const refreshed = await refreshSession();
    if (!refreshed) {
      await clearSession();
      return NextResponse.json(
        { error: { code: "unauthenticated", message: "Your session has expired." } },
        { status: 401 },
      );
    }
    response = await forward(target, method, body, contentType, refreshed);
  }

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "application/json",
      "Cache-Control": "no-store",
    },
  });
}

async function forward(
  target: string,
  method: ForwardedMethod,
  body: ArrayBuffer | undefined,
  contentType: string,
  token: string | undefined,
): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body && body.byteLength > 0) headers["Content-Type"] = contentType;

  return fetch(target, {
    method,
    headers,
    body: body && body.byteLength > 0 ? body : undefined,
    cache: "no-store",
    redirect: "manual",
  });
}

/** Exchange the refresh cookie for a new access token. Returns the token on success. */
async function refreshSession(): Promise<string | undefined> {
  const refresh = await getRefreshToken();
  if (!refresh) return undefined;
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
    cache: "no-store",
  });
  if (!response.ok) return undefined;
  const payload = (await response.json().catch(() => ({}))) as { access?: string };
  if (!payload.access) return undefined;
  await setAccessToken(payload.access);
  return payload.access;
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const PUT = handle;
export const DELETE = handle;
export const dynamic = "force-dynamic";
