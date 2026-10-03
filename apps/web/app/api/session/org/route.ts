/**
 * Switch the active organization.
 *
 * The requested id is validated against the caller's real memberships (fetched
 * from the API with their own token) before it is stored, so a tampered cookie
 * cannot widen access — the API would reject the resulting requests anyway.
 */
import { NextResponse } from "next/server";

import { apiFetch } from "@/lib/api-server";
import { setSelectedOrgId } from "@/lib/session";
import type { CurrentUser } from "@/lib/types";

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as { organizationId?: string };
  const organizationId = body.organizationId;
  if (!organizationId) {
    return NextResponse.json(
      { error: { code: "bad_request", message: "organizationId is required." } },
      { status: 400 },
    );
  }

  const me = await apiFetch<CurrentUser>("/api/v1/me/");
  const allowed = me.memberships.some((m) => m.organization_id === organizationId);
  if (!allowed) {
    return NextResponse.json(
      { error: { code: "forbidden", message: "You are not a member of that organization." } },
      { status: 403 },
    );
  }

  await setSelectedOrgId(organizationId);
  return NextResponse.json({ organization_id: organizationId });
}
