import Link from "next/link";

import { Card, CardHeader, EmptyState, PageHeader, StatusBadge } from "@/components/ui";
import { apiFetch } from "@/lib/api-server";
import { formatDuration, formatRelative, titleCase } from "@/lib/format";
import { loadSession } from "@/lib/server-session";
import type { Execution, Paginated } from "@/lib/types";

export const metadata = { title: "Executions" };

const FILTERS = [
  { label: "All", value: "" },
  { label: "Succeeded", value: "succeeded" },
  { label: "Failed", value: "failed" },
  { label: "Running", value: "running" },
];

export default async function ExecutionsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; page?: string }>;
}) {
  const { organizationId } = await loadSession();
  const params = await searchParams;
  const status = params.status ?? "";
  const page = Number(params.page ?? "1") || 1;

  const query = new URLSearchParams({ page: String(page), page_size: "25" });
  if (status) query.set("status", status);

  const executions = await apiFetch<Paginated<Execution>>(
    `/api/v1/orgs/${organizationId}/analytics/executions/?${query.toString()}`,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Execution History"
        description="Every AI run is recorded with the tools it used, its model, token usage and duration. Analyst runs are also visible as conversations."
      />

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter by status">
        {FILTERS.map((filter) => {
          const active = status === filter.value;
          return (
            <Link
              key={filter.label}
              href={filter.value ? `/executions?status=${filter.value}` : "/executions"}
              role="tab"
              aria-selected={active}
              className={`rounded-full border px-3 py-1 text-xs font-medium ${
                active
                  ? "border-[var(--color-brand-500)] bg-[var(--color-brand-50)] text-[var(--color-brand-700)]"
                  : "border-[var(--color-line)] bg-white/5 text-[var(--color-ink-700)] hover:bg-white/10"
              }`}
            >
              {filter.label}
            </Link>
          );
        })}
      </div>

      <Card>
        <CardHeader title="Runs" description={`${executions.count} execution(s)${status ? ` · ${status}` : ""}.`} />
        {executions.results.length === 0 ? (
          <EmptyState
            title="No executions found"
            description="Try a different status filter, or ask a question in the AI Analyst."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-canvas)] text-left text-xs uppercase tracking-wide text-[var(--color-ink-500)]">
                <tr>
                  <th scope="col" className="px-5 py-2">Question / run</th>
                  <th scope="col" className="px-5 py-2">Kind</th>
                  <th scope="col" className="px-5 py-2">Status</th>
                  <th scope="col" className="px-5 py-2">Duration</th>
                  <th scope="col" className="px-5 py-2">Started</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-line)]">
                {executions.results.map((execution) => (
                  <tr key={execution.id}>
                    <td className="px-5 py-3">
                      <Link
                        href={`/executions/${execution.id}`}
                        className="font-medium text-[var(--color-ink-900)] hover:underline"
                      >
                        {execution.question || titleCase(execution.kind)}
                      </Link>
                      <p className="text-xs text-[var(--color-ink-500)]">
                        {execution.user_email ?? "system"}
                        {execution.datasource_name ? ` · ${execution.datasource_name}` : ""}
                      </p>
                    </td>
                    <td className="px-5 py-3 text-[var(--color-ink-700)]">{titleCase(execution.kind)}</td>
                    <td className="px-5 py-3"><StatusBadge status={execution.status} /></td>
                    <td className="px-5 py-3 text-[var(--color-ink-700)]">{formatDuration(execution.duration_ms)}</td>
                    <td className="px-5 py-3 text-[var(--color-ink-500)]">{formatRelative(execution.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {executions.total_pages > 1 ? (
        <nav aria-label="Pagination" className="flex items-center justify-between text-sm">
          <Link
            href={`/executions?${new URLSearchParams({ ...(status ? { status } : {}), page: String(Math.max(1, page - 1)) }).toString()}`}
            aria-disabled={page <= 1}
            className={page <= 1 ? "pointer-events-none text-[var(--color-ink-500)] opacity-50" : "text-[var(--color-brand-600)]"}
          >
            ← Previous
          </Link>
          <span className="text-[var(--color-ink-500)]">
            Page {executions.page} of {executions.total_pages}
          </span>
          <Link
            href={`/executions?${new URLSearchParams({ ...(status ? { status } : {}), page: String(Math.min(executions.total_pages, page + 1)) }).toString()}`}
            aria-disabled={page >= executions.total_pages}
            className={page >= executions.total_pages ? "pointer-events-none text-[var(--color-ink-500)] opacity-50" : "text-[var(--color-brand-600)]"}
          >
            Next →
          </Link>
        </nav>
      ) : null}
    </div>
  );
}
