/**
 * Session cookie helpers.
 *
 * Tokens live in httpOnly cookies so no script in the browser can read them. The
 * access token is short-lived; the refresh token is rotated server-side on each
 * refresh call (see the API's SIMPLE_JWT settings).
 */
import { cookies } from "next/headers";

export const ACCESS_COOKIE = "df_access";
export const REFRESH_COOKIE = "df_refresh";
export const ORG_COOKIE = "df_org";

const ACCESS_MAX_AGE = 60 * 15; // 15 minutes, mirrors the access token TTL
const REFRESH_MAX_AGE = 60 * 60 * 24 * 7;

function baseOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
  };
}

export async function getAccessToken(): Promise<string | undefined> {
  return (await cookies()).get(ACCESS_COOKIE)?.value;
}

export async function getRefreshToken(): Promise<string | undefined> {
  return (await cookies()).get(REFRESH_COOKIE)?.value;
}

export async function getSelectedOrgId(): Promise<string | undefined> {
  return (await cookies()).get(ORG_COOKIE)?.value;
}

export async function setSessionTokens(access: string, refresh: string): Promise<void> {
  const store = await cookies();
  store.set(ACCESS_COOKIE, access, { ...baseOptions(), maxAge: ACCESS_MAX_AGE });
  store.set(REFRESH_COOKIE, refresh, { ...baseOptions(), maxAge: REFRESH_MAX_AGE });
}

export async function setAccessToken(access: string): Promise<void> {
  (await cookies()).set(ACCESS_COOKIE, access, { ...baseOptions(), maxAge: ACCESS_MAX_AGE });
}

export async function setSelectedOrgId(orgId: string): Promise<void> {
  (await cookies()).set(ORG_COOKIE, orgId, {
    ...baseOptions(),
    httpOnly: false, // the client reads this to render the org switcher
    maxAge: REFRESH_MAX_AGE,
  });
}

export async function clearSession(): Promise<void> {
  const store = await cookies();
  for (const name of [ACCESS_COOKIE, REFRESH_COOKIE, ORG_COOKIE]) {
    store.set(name, "", { ...baseOptions(), maxAge: 0 });
  }
}
