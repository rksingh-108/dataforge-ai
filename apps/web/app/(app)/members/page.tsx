import { MemberManager } from "@/components/MemberManager";
import { Card, CardHeader, PageHeader } from "@/components/ui";
import { apiFetch } from "@/lib/api-server";
import { loadSession } from "@/lib/server-session";

export const metadata = { title: "Users & Roles" };

interface MembershipRow {
  id: string;
  user: string;
  user_email: string;
  user_name: string;
  role: string;
  is_active: boolean;
  permissions: string[];
  created_at: string;
}

const ROLE_MATRIX: { role: string; summary: string; abilities: string }[] = [
  { role: "Owner", summary: "Full control", abilities: "Everything an admin can do, plus organization ownership." },
  { role: "Admin", summary: "Administration", abilities: "Manage members, data sources, documents, audit logs and analytics." },
  { role: "Analyst", summary: "Analysis", abilities: "Ask the analyst, upload documents, view data sources and executions." },
  { role: "Viewer", summary: "Read-only", abilities: "View data sources, documents and execution history." },
];

export default async function MembersPage() {
  const { currentUser, membership, organizationId } = await loadSession();
  const members = await apiFetch<MembershipRow[]>(
    `/api/v1/orgs/${organizationId}/members/`,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Users & Roles"
        description="Roles are organization-scoped and enforced by the API on every request. This page only reflects what the server allows."
      />

      <MemberManager
        organizationId={organizationId}
        members={members}
        currentUserId={currentUser.user.id}
        myPermissions={membership.permissions}
      />

      <Card>
        <CardHeader title="Role reference" description="What each role can do." />
        <ul className="divide-y divide-[var(--color-line)]">
          {ROLE_MATRIX.map((entry) => (
            <li key={entry.role} className="px-5 py-3">
              <p className="text-sm font-medium text-[var(--color-ink-900)]">
                {entry.role} <span className="font-normal text-[var(--color-ink-500)]">— {entry.summary}</span>
              </p>
              <p className="text-xs text-[var(--color-ink-500)]">{entry.abilities}</p>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
