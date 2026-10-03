/**
 * BFF login.
 *
 * The browser posts credentials to this same-origin route. We forward them to
 * Django, then store the returned tokens in httpOnly cookies and return only the
 * user profile to the client. Tokens never reach JavaScript.
 */
import { NextResponse } from "next/server";

import { API_BASE_URL } from "@/lib/api-server";
import { clearSession, setSelectedOrgId, setSessionTokens } from "@/lib/session";

export async function POST(request: Request) {
  let credentials: { email?: string; password?: string };
  try {
    credentials = await request.json();
  } catch {
    return NextResponse.json(
      { error: { code: "bad_request", message: "A JSON body is required." } },
      { status: 400 },
    );
  }

  const upstream = await fetch(`${API_BASE_URL}/api/v1/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(credentials),
    cache: "no-store",
  });

  const payload = await upstream.json().catch(() => ({}));
  if (!upstream.ok) {
    // Clear any stale session so a failed login cannot leave a partial cookie.
    await clearSession();
    return NextResponse.json(payload, { status: upstream.status });
  }

  await setSessionTokens(payload.access, payload.refresh);
  const first = payload.memberships?.[0];
  if (first?.organization_id) {
    await setSelectedOrgId(first.organization_id);
  }

  return NextResponse.json({
    user: payload.user,
    memberships: payload.memberships ?? [],
  });
}
