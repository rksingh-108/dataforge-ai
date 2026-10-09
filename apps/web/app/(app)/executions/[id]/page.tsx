import Link from "next/link";
import { notFound } from "next/navigation";

import { Badge, Card, CardHeader, EmptyState, PageHeader, StatusBadge } from "@/components/ui";
import { ApiRequestError, apiFetch } from "@/lib/api-server";
import { formatDateTime, formatDuration, titleCase } from "@/lib/format";
import { loadSession } from "@/lib/server-session";
import type { Execution } from "@/lib/types";

export const metadata = { title: "Execution" };

export default async function ExecutionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { organizationId } = await loadSession();

  let execution: Execution;
  try {
    execution = await apiFetch<Execution>(
      `/api/v1/orgs/${organizationId}/analytics/executions/${id}/`,
    );
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) notFound();
    throw error;
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href="/executions" className="text-xs text-[var(--color-brand-600)] hover:underline">
          ← Back to executions
        </Link>
      </div>

      <PageHeader
        title={execution.question || titleCase(execution.kind)}
        description={`${titleCase(execution.kind)} · started ${formatDateTime(execution.started_at)}`}
        actions={<StatusBadge status={execution.status} />}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Duration" value={formatDuration(execution.duration_ms)} />
        <Metric label="Tokens" value={execution.total_tokens} />
        <Metric label="Provider" value={execution.provider || "—"} />
        <Metric label="Model" value={execution.model_name || "—"} />
      </div>

      {execution.error ? (
        <Card className="border-red-400/25 bg-red-400/10 p-5">
          <p className="text-sm font-medium text-[var(--color-danger)]">{execution.error}</p>
        </Card>
      ) : null}

      <Card>
        <CardHeader
          title="Answer"
          description="Produced from tool results only. Private model reasoning is not stored or shown."
        />
        <div className="whitespace-pre-wrap p-5 text-sm text-[var(--color-ink-900)]">
          {execution.answer || "No answer was produced for this run."}
        </div>
      </Card>

      <Card>
        <CardHeader title="Tools used" description="High-level trace of each tool invocation." />
        {(execution.steps ?? []).length === 0 ? (
          <EmptyState title="No tools were used" description="This run produced an answer without calling a tool." />
        ) : (
          <ol className="divide-y divide-[var(--color-line)]">
            {(execution.steps ?? []).map((step) => (
              <li key={step.id} className="px-5 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={step.status === "failed" ? "danger" : "brand"}>
                    {titleCase(step.tool_name || "step")}
                  </Badge>
                  <span className="text-sm font-medium text-[var(--color-ink-900)]">{step.title}</span>
                  <span className="text-xs text-[var(--color-ink-500)]">{formatDuration(step.duration_ms)}</span>
                </div>

                {step.input_summary && Object.keys(step.input_summary).length > 0 ? (
                  <Detail label="Input" value={step.input_summary} />
                ) : null}
                {step.output_summary && Object.keys(step.output_summary).length > 0 ? (
                  <Detail label="Output" value={step.output_summary} />
                ) : null}
                {step.error ? (
                  <p className="mt-2 text-xs text-[var(--color-danger)]">{step.error}</p>
                ) : null}
              </li>
            ))}
          </ol>
        )}
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-ink-500)]">{label}</p>
      <p className="mt-1 text-lg font-semibold text-[var(--color-ink-900)]">{value}</p>
    </Card>
  );
}

function Detail({ label, value }: { label: string; value: Record<string, unknown> }) {
  return (
    <div className="mt-2">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-ink-500)]">{label}</p>
      <pre className="mt-1 overflow-x-auto rounded bg-[var(--color-canvas)] p-2 text-xs text-[var(--color-ink-700)]">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}
