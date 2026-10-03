import Link from "next/link";

import { Card, CardHeader, EmptyState, PageHeader, StatTile, StatusBadge } from "@/components/ui";
import { apiFetch } from "@/lib/api-server";
import { formatDuration, formatRelative } from "@/lib/format";
import { Permission, hasPermission } from "@/lib/permissions";
import { loadSession } from "@/lib/server-session";
import type { Execution, Insights, Paginated } from "@/lib/types";

export const metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const { membership, organizationId } = await loadSession();
  const permissions = membership.permissions;

  const [insights, executions] = await Promise.all([
    apiFetch<Insights>(`/api/v1/orgs/${organizationId}/analytics/insights/`),
    apiFetch<Paginated<Execution>>(`/api/v1/orgs/${organizationId}/analytics/executions/?page_size=6`),
  ]);

  const canAsk = hasPermission(permissions, Permission.AnalystQuery);

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome to ${membership.organization_name}`}
        description="A live view of AI activity in your organization. All figures are computed from recorded executions."
      />

      <section aria-label="Execution summary" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Executions" value={insights.executions.total} hint="All time" />
        <StatTile
          label="Succeeded"
          value={insights.executions.succeeded}
          hint={`${insights.executions.success_rate_percent}% success rate`}
        />
        <StatTile label="Failed" value={insights.executions.failed} hint="Needs attention" />
        <StatTile label="Running" value={insights.executions.running} hint="In flight right now" />
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Recent executions"
            description="The latest AI runs in this organization."
            actions={
              <Link
                href="/executions"
                className="text-xs font-medium text-[var(--color-brand-600)] hover:underline"
              >
                View all
              </Link>
            }
          />
          {executions.results.length === 0 ? (
            <EmptyState
              title="No executions yet"
              description={
                canAsk
                  ? "Ask your first question in the AI Analyst to see activity here."
                  : "Ask an analyst or admin to run a query."
              }
            />
          ) : (
            <ul className="divide-y divide-[var(--color-line)]">
              {executions.results.map((execution) => (
                <li key={execution.id} className="flex items-start justify-between gap-4 px-5 py-3">
                  <div className="min-w-0">
                    <Link
                      href={`/executions/${execution.id}`}
                      className="truncate text-sm font-medium text-[var(--color-ink-900)] hover:underline"
                    >
                      {execution.question || execution.kind}
                    </Link>
                    <p className="mt-0.5 text-xs text-[var(--color-ink-500)]">
                      {formatRelative(execution.created_at)} ·{" "}
                      {execution.user_email ?? "system"} · {formatDuration(execution.duration_ms)}
                    </p>
                  </div>
                  <StatusBadge status={execution.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Most used tools" description="Across all executions." />
            {insights.top_tools.length === 0 ? (
              <EmptyState title="No tool usage yet" description="Tool usage appears after the first run." />
            ) : (
              <ul className="divide-y divide-[var(--color-line)]">
                {insights.top_tools.map((tool) => (
                  <li
                    key={tool.tool}
                    className="flex items-center justify-between px-5 py-2.5 text-sm"
                  >
                    <span className="font-medium text-[var(--color-ink-700)]">{tool.tool}</span>
                    <span className="text-[var(--color-ink-500)]">{tool.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {canAsk ? (
            <Card className="p-5">
              <h2 className="text-sm font-semibold text-[var(--color-ink-900)]">Ask the analyst</h2>
              <p className="mt-1 text-xs text-[var(--color-ink-500)]">
                Questions are answered with read-only SQL over connected databases and cited
                document passages.
              </p>
              <Link
                href="/analyst"
                className="mt-3 inline-flex rounded-md bg-[var(--color-brand-600)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--color-brand-700)]"
              >
                Open AI Analyst
              </Link>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
