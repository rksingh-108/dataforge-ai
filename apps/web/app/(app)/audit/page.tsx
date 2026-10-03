import { Card, CardHeader, EmptyState, PageHeader } from "@/components/ui";
import { apiFetch } from "@/lib/api-server";
import { formatDateTime, titleCase } from "@/lib/format";
import { loadSession } from "@/lib/server-session";
import type { AuditLogEntry, Paginated } from "@/lib/types";

export const metadata = { title: "Audit Logs" };

export default async function AuditPage() {
  const { organizationId } = await loadSession();
  const logs = await apiFetch<Paginated<AuditLogEntry>>(
    `/api/v1/orgs/${organizationId}/analytics/audit-logs/?page_size=50`,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Logs"
        description="Append-only record of security-relevant actions in this organization, including credential access by the AI service. Entries cannot be edited or deleted."
      />

      <Card>
        <CardHeader title="Events" description={`${logs.count} recorded event(s).`} />
        {logs.results.length === 0 ? (
          <EmptyState
            title="No audit events yet"
            description="Audit entries appear here as soon as your organization performs actions."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-canvas)] text-left text-xs uppercase tracking-wide text-[var(--color-ink-500)]">
                <tr>
                  <th scope="col" className="px-5 py-2">Action</th>
                  <th scope="col" className="px-5 py-2">Actor</th>
                  <th scope="col" className="px-5 py-2">Target</th>
                  <th scope="col" className="px-5 py-2">When</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-line)]">
                {logs.results.map((entry) => (
                  <tr key={entry.id}>
                    <td className="px-5 py-3 font-medium text-[var(--color-ink-900)]">
                      {entry.action}
                    </td>
                    <td className="px-5 py-3 text-[var(--color-ink-700)]">
                      {entry.actor_email ?? "system"}
                    </td>
                    <td className="px-5 py-3 text-[var(--color-ink-500)]">
                      {entry.target_type ? `${titleCase(entry.target_type)} ${entry.target_id.slice(0, 8)}` : "—"}
                    </td>
                    <td className="px-5 py-3 text-[var(--color-ink-500)]">
                      {formatDateTime(entry.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
