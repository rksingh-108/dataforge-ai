/** BFF logout: blacklist the refresh token server-side, then clear cookies. */
import { NextResponse } from "next/server";

import { API_BASE_URL } from "@/lib/api-server";
import { clearSession, getAccessToken, getRefreshToken } from "@/lib/session";

export async function POST() {
  const [access, refresh] = await Promise.all([getAccessToken(), getRefreshToken()]);
  if (access && refresh) {
    // Best effort: an expired token is not an error for logout.
    await fetch(`${API_BASE_URL}/api/v1/auth/logout/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${access}`,
      },
      body: JSON.stringify({ refresh }),
      cache: "no-store",
    }).catch(() => undefined);
  }
  await clearSession();
  return NextResponse.json({ ok: true });
}
