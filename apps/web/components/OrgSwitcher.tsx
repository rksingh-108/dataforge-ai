"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { MembershipSummary } from "@/lib/types";

export function OrgSwitcher({
  memberships,
  activeId,
}: {
  memberships: MembershipSummary[];
  activeId: string;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  async function onChange(organizationId: string) {
    setError(null);
    const response = await fetch("/api/session/org", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ organizationId }),
    });
    if (!response.ok) {
      setError("Could not switch organization.");
      return;
    }
    startTransition(() => {
      router.refresh();
    });
  }

  if (memberships.length <= 1) {
    return (
      <p className="px-3 py-2 text-sm font-medium text-[var(--color-ink-900)]">
        {memberships[0]?.organization_name ?? "No organization"}
      </p>
    );
  }

  return (
    <div className="px-3 py-2">
      <label htmlFor="org-switcher" className="sr-only">
        Active organization
      </label>
      <select
        id="org-switcher"
        value={activeId}
        disabled={pending}
        onChange={(event) => void onChange(event.target.value)}
        className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-2)] px-2 py-1.5 text-sm text-[var(--color-ink-900)]"
      >
        {memberships.map((membership) => (
          <option key={membership.organization_id} value={membership.organization_id}>
            {membership.organization_name} ({membership.role})
          </option>
        ))}
      </select>
      {error ? (
        <p role="alert" className="mt-1 text-xs text-[var(--color-danger)]">
          {error}
        </p>
      ) : null}
    </div>
  );
}
