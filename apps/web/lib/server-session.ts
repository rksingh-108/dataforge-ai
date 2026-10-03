/**
 * Resolves the caller's session and active organization for server components.
 *
 * Lives outside `lib/session.ts` so that cookie plumbing and domain loading stay
 * separate concerns.
 */
import { redirect } from "next/navigation";

import { ApiRequestError, apiFetch } from "@/lib/api-server";
import { getSelectedOrgId } from "@/lib/session";
import type { CurrentUser, MembershipSummary } from "@/lib/types";

export interface ActiveSession {
  currentUser: CurrentUser;
  membership: MembershipSummary;
  memberships: MembershipSummary[];
  organizationId: string;
}

export async function loadSession(): Promise<ActiveSession> {
  let currentUser: CurrentUser;
  try {
    currentUser = await apiFetch<CurrentUser>("/api/v1/me/");
  } catch (error) {
    if (error instanceof ApiRequestError && (error.status === 401 || error.status === 403)) {
      redirect("/login");
    }
    throw error;
  }

  if (currentUser.memberships.length === 0) {
    redirect("/no-organization");
  }

  const preferred = await getSelectedOrgId();
  const membership =
    currentUser.memberships.find((m) => m.organization_id === preferred) ??
    currentUser.memberships[0]!;

  return {
    currentUser,
    membership,
    memberships: currentUser.memberships,
    organizationId: membership.organization_id,
  };
}
