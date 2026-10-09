"use client";

import { useState } from "react";

import { Button } from "@/components/Button";
import { Badge, EmptyState, ErrorBanner, Spinner, StatusBadge } from "@/components/ui";
import { ClientApiError, clientFetch } from "@/lib/api-client";
import { formatDuration, titleCase } from "@/lib/format";
import type { Execution, ExecutionStep } from "@/lib/types";

interface DatasourceOption {
  id: string;
  name: string;
  engine: string;
  tableCount: number;
}

const EXAMPLES = [
  "How many orders were placed last month?",
  "Summarise our refund policy and when it changed.",
  "Which customers have the highest total order value?",
];

export function AnalystConsole({
  organizationId,
  datasources,
}: {
  organizationId: string;
  datasources: DatasourceOption[];
}) {
  const [question, setQuestion] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [useDocuments, setUseDocuments] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<{ message: string; code?: string } | null>(null);
  const [result, setResult] = useState<Execution | null>(null);

  function toggleSource(id: string) {
    setSelected((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim() || running) return;

    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const execution = await clientFetch<Execution>(
        `/api/v1/orgs/${organizationId}/analyst/query/`,
        {
          method: "POST",
          body: {
            question: question.trim(),
            datasource_ids: selected,
            use_documents: useDocuments,
          },
        },
      );
      setResult(execution);
      setQuestion("");
    } catch (caught) {
      if (caught instanceof ClientApiError) {
        setError({ message: caught.message, code: caught.code });
      } else {
        setError({ message: "The analysis could not be started." });
      }
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="divide-y divide-[var(--color-line)]">
      <form onSubmit={onSubmit} className="space-y-4 p-5">
        <div className="space-y-1">
          <label htmlFor="question" className="block text-sm font-medium text-[var(--color-ink-700)]">
            Your question
          </label>
          <textarea
            id="question"
            rows={3}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="e.g. What was total revenue for the last quarter?"
            className="w-full resize-y rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-ink-900)] placeholder:text-[var(--color-ink-500)]"
          />
          <p className="text-xs text-[var(--color-ink-500)]">
            Answers are grounded in your connected data and documents. The model never receives
            unrestricted database access.
          </p>
        </div>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-[var(--color-ink-700)]">Data sources</legend>
          {datasources.length === 0 ? (
            <p className="text-xs text-[var(--color-ink-500)]">
              No connected data sources are available. Add one under Data Sources.
            </p>
          ) : (
            <ul className="flex flex-wrap gap-2">
              {datasources.map((source) => {
                const active = selected.includes(source.id);
                return (
                  <li key={source.id}>
                    <button
                      type="button"
                      aria-pressed={active}
                      onClick={() => toggleSource(source.id)}
                      className={`rounded-full border px-3 py-1 text-xs font-medium ${
                        active
                          ? "border-[var(--color-brand-500)] bg-[var(--color-brand-50)] text-[var(--color-brand-700)]"
                          : "border-[var(--color-line)] bg-white/5 text-[var(--color-ink-700)] hover:bg-white/10"
                      }`}
                    >
                      {source.name} · {source.engine} · {source.tableCount} tables
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          {selected.length === 0 && datasources.length > 0 ? (
            <p className="text-xs text-[var(--color-ink-500)]">
              No source selected — the analyst will only search documents.
            </p>
          ) : null}
        </fieldset>

        <label className="flex items-center gap-2 text-sm text-[var(--color-ink-700)]">
          <input
            type="checkbox"
            checked={useDocuments}
            onChange={(event) => setUseDocuments(event.target.checked)}
          />
          Include uploaded documents in the search
        </label>

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" loading={running}>
            {running ? "Analysing" : "Ask the analyst"}
          </Button>
          {running ? <Spinner label="Running tools" /> : null}
        </div>
      </form>

      {error ? (
        <div className="p-5">
          <ErrorBanner message={error.message} code={error.code} />
        </div>
      ) : null}

      {result ? <ResultPanel execution={result} /> : null}

      {!result && !running && !error ? (
        <EmptyState
          title="No analysis yet"
          description="Ask a question to see the tools the analyst uses, the queries it runs, and the answer with its sources."
          action={
            <ul className="flex flex-wrap justify-center gap-2">
              {EXAMPLES.map((example) => (
                <li key={example}>
                  <button
                    type="button"
                    onClick={() => setQuestion(example)}
                    className="rounded-full border border-[var(--color-line)] bg-white/5 px-3 py-1 text-xs text-[var(--color-ink-700)] transition hover:bg-white/10 hover:text-[var(--color-ink-900)]"
                  >
                    {example}
                  </button>
                </li>
              ))}
            </ul>
          }
        />
      ) : null}
    </div>
  );
}

function ResultPanel({ execution }: { execution: Execution }) {
  const steps = execution.steps ?? [];
  return (
    <div className="space-y-5 p-5">
      <div className="flex flex-wrap items-center gap-3">
        <StatusBadge status={execution.status} />
        <span className="text-xs text-[var(--color-ink-500)]">
          {formatDuration(execution.duration_ms)} · {execution.total_tokens} tokens ·{" "}
          {execution.provider || "provider"} {execution.model_name ? `· ${execution.model_name}` : ""}
        </span>
      </div>

      {execution.error ? <ErrorBanner message={execution.error} /> : null}

      {steps.length > 0 ? (
        <section aria-label="Tools used">
          <h3 className="mb-2 text-sm font-semibold text-[var(--color-ink-900)]">How this was answered</h3>
          <ol className="space-y-2">
            {steps.map((step) => (
              <li
                key={step.id}
                className="rounded-md border border-[var(--color-line)] bg-[var(--color-canvas)] p-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={step.status === "failed" ? "danger" : "brand"}>
                    {titleCase(step.tool_name || "step")}
                  </Badge>
                  <span className="text-sm font-medium text-[var(--color-ink-900)]">
                    {step.title || titleCase(step.tool_name)}
                  </span>
                  <span className="text-xs text-[var(--color-ink-500)]">
                    {formatDuration(step.duration_ms)}
                  </span>
                </div>
                <StepDetail step={step} />
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      <section aria-label="Answer">
        <h3 className="mb-2 text-sm font-semibold text-[var(--color-ink-900)]">Answer</h3>
        <div className="whitespace-pre-wrap rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-2)] p-4 text-sm text-[var(--color-ink-900)]">
          {execution.answer || "No answer was produced."}
        </div>
      </section>
    </div>
  );
}

function StepDetail({ step }: { step: ExecutionStep }) {
  const summary = step.output_summary ?? {};
  const rows = typeof summary.row_count === "number" ? summary.row_count : undefined;
  const matches = typeof summary.match_count === "number" ? summary.match_count : undefined;
  const flagged = Array.isArray(summary.content_flagged) && summary.content_flagged.length > 0;
  const rejected = summary.rejected === true;

  if (step.error) {
    return <p className="mt-1 text-xs text-[var(--color-danger)]">{step.error}</p>;
  }
  return (
    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[var(--color-ink-500)]">
      {rows !== undefined ? <span>{rows} rows returned</span> : null}
      {matches !== undefined ? <span>{matches} document passages</span> : null}
      {rejected ? <Badge tone="warn">query rejected by validator</Badge> : null}
      {flagged ? <Badge tone="warn">untrusted content flagged</Badge> : null}
    </div>
  );
}
