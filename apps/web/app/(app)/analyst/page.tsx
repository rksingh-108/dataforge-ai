import { Card } from "@/components/ui";
import { AnalystConsole } from "@/components/AnalystConsole";
import { apiFetch } from "@/lib/api-server";
import { loadSession } from "@/lib/server-session";
import type { DataSource, Paginated } from "@/lib/types";

export const metadata = { title: "AI Analyst" };

export default async function AnalystPage() {
  const { organizationId } = await loadSession();
  const datasources = await apiFetch<Paginated<DataSource>>(
    `/api/v1/orgs/${organizationId}/datasources/?page_size=100`,
  );

  const available = datasources.results.filter((source) => source.status === "connected");

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">AI Analyst</h1>
        <p className="mt-1 max-w-2xl text-sm text-[var(--color-ink-500)]">
          Ask a question in plain language. The analyst chooses tools, runs validated read-only
          SQL against connected databases, searches your documents, and answers with sources.
        </p>
      </header>

      <Card className="p-0">
        <AnalystConsole
          organizationId={organizationId}
          datasources={available.map((source) => ({
            id: source.id,
            name: source.name,
            engine: source.engine,
            tableCount: source.table_count,
          }))}
        />
      </Card>
    </div>
  );
}
