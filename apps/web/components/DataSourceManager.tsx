"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/Button";
import { Badge, Card, CardHeader, EmptyState, ErrorBanner, StatusBadge } from "@/components/ui";
import { ClientApiError, clientFetch } from "@/lib/api-client";
import { formatBytes, formatRelative, titleCase } from "@/lib/format";
import type { DataSource, Paginated } from "@/lib/types";

interface FormState {
  name: string;
  engine: "postgresql" | "mysql";
  host: string;
  port: string;
  database_name: string;
  username: string;
  password: string;
  description: string;
}

const BLANK: FormState = {
  name: "",
  engine: "postgresql",
  host: "",
  port: "5432",
  database_name: "",
  username: "",
  password: "",
  description: "",
};

export function DataSourceManager({
  organizationId,
  datasources,
  canManage,
}: {
  organizationId: string;
  datasources: DataSource[];
  canManage: boolean;
}) {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(BLANK);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<{ message: string; code?: string } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const base = `/api/v1/orgs/${organizationId}/datasources`;

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function onCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("create");
    setError(null);
    setNotice(null);
    try {
      await clientFetch<DataSource>(base + "/", {
        method: "POST",
        body: { ...form, port: Number(form.port) },
      });
      setForm(BLANK);
      setShowForm(false);
      setNotice("Data source created. Run a connection test next.");
      router.refresh();
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(null);
    }
  }

  async function onTest(source: DataSource) {
    setBusy(`test:${source.id}`);
    setError(null);
    setNotice(null);
    try {
      const result = await clientFetch<{ ok: boolean; server_version: string; error: string }>(
        `${base}/${source.id}/test/`,
        { method: "POST" },
      );
      setNotice(
        result.ok
          ? `Connected to ${source.name} (${result.server_version || "unknown version"}).`
          : `Connection failed: ${result.error}`,
      );
      router.refresh();
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(null);
    }
  }

  async function onSync(source: DataSource) {
    setBusy(`sync:${source.id}`);
    setError(null);
    setNotice(null);
    try {
      const result = await clientFetch<{ tables: number; columns: number }>(
        `${base}/${source.id}/sync/`,
        { method: "POST" },
      );
      setNotice(`Discovered ${result.tables} tables and ${result.columns} columns.`);
      router.refresh();
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(null);
    }
  }

  async function onDelete(source: DataSource) {
    if (!window.confirm(`Delete "${source.name}"? This cannot be undone.`)) return;
    setBusy(`delete:${source.id}`);
    setError(null);
    try {
      await clientFetch(`${base}/${source.id}/`, { method: "DELETE" });
      router.refresh();
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      {error ? <ErrorBanner message={error.message} code={error.code} /> : null}
      {notice ? (
        <div
          role="status"
          className="rounded-lg border border-emerald-400/25 bg-emerald-400/10 px-4 py-3 text-sm text-[var(--color-ok)]"
        >
          {notice}
        </div>
      ) : null}

      {canManage ? (
        <div className="flex justify-end">
          <Button variant="secondary" onClick={() => setShowForm((value) => !value)}>
            {showForm ? "Cancel" : "Add data source"}
          </Button>
        </div>
      ) : null}

      {showForm && canManage ? (
        <Card>
          <CardHeader
            title="New data source"
            description="Use a read-only database account. The host is validated to prevent server-side request forgery."
          />
          <form onSubmit={onCreate} className="grid gap-4 p-5 sm:grid-cols-2">
            <Field label="Name" id="name" required value={form.name}
                   onChange={(value) => update("name", value)} />
            <Field label="Engine" id="engine" as="select" value={form.engine}
                   onChange={(value) => {
                     update("engine", value as FormState["engine"]);
                     update("port", value === "mysql" ? "3306" : "5432");
                   }} options={["postgresql", "mysql"]} />
            <Field label="Host" id="host" required value={form.host}
                   onChange={(value) => update("host", value)} placeholder="db.example.com" />
            <Field label="Port" id="port" required type="number" value={form.port}
                   onChange={(value) => update("port", value)} />
            <Field label="Database" id="database_name" required value={form.database_name}
                   onChange={(value) => update("database_name", value)} />
            <Field label="Username" id="username" required value={form.username}
                   onChange={(value) => update("username", value)} />
            <Field label="Password" id="password" required type="password" value={form.password}
                   onChange={(value) => update("password", value)}
                   hint="Encrypted immediately; never returned by the API." />
            <Field label="Description" id="description" value={form.description}
                   onChange={(value) => update("description", value)} />
            <div className="sm:col-span-2">
              <Button type="submit" loading={busy === "create"}>
                Create data source
              </Button>
            </div>
          </form>
        </Card>
      ) : null}

      <Card>
        <CardHeader
          title="Connected databases"
          description={`${datasources.length} data source${datasources.length === 1 ? "" : "s"} in this organization.`}
        />
        {datasources.length === 0 ? (
          <EmptyState
            title="No data sources yet"
            description="Connect a PostgreSQL or MySQL database to let the analyst run read-only queries against it."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-canvas)] text-left text-xs uppercase tracking-wide text-[var(--color-ink-500)]">
                <tr>
                  <th scope="col" className="px-5 py-2">Name</th>
                  <th scope="col" className="px-5 py-2">Engine</th>
                  <th scope="col" className="px-5 py-2">Status</th>
                  <th scope="col" className="px-5 py-2">Schema</th>
                  <th scope="col" className="px-5 py-2">Last tested</th>
                  {canManage ? <th scope="col" className="px-5 py-2 text-right">Actions</th> : null}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-line)]">
                {datasources.map((source) => (
                  <tr key={source.id}>
                    <td className="px-5 py-3">
                      <p className="font-medium text-[var(--color-ink-900)]">{source.name}</p>
                      <p className="text-xs text-[var(--color-ink-500)]">
                        {source.host}:{source.port}/{source.database_name}
                      </p>
                    </td>
                    <td className="px-5 py-3">
                      <Badge tone="neutral">{source.engine}</Badge>
                      {source.is_read_only ? (
                        <span className="ml-2 text-xs text-[var(--color-ink-500)]">read-only</span>
                      ) : null}
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge status={source.status} />
                      {source.last_error ? (
                        <p className="mt-1 max-w-xs truncate text-xs text-[var(--color-danger)]"
                           title={source.last_error}>
                          {source.last_error}
                        </p>
                      ) : null}
                    </td>
                    <td className="px-5 py-3 text-[var(--color-ink-700)]">
                      {source.table_count} tables
                    </td>
                    <td className="px-5 py-3 text-[var(--color-ink-500)]">
                      {formatRelative(source.last_tested_at)}
                    </td>
                    {canManage ? (
                      <td className="px-5 py-3">
                        <div className="flex justify-end gap-2">
                          <Button variant="secondary" onClick={() => void onTest(source)}
                                  loading={busy === `test:${source.id}`}>
                            Test
                          </Button>
                          <Button variant="secondary" onClick={() => void onSync(source)}
                                  loading={busy === `sync:${source.id}`}>
                            Sync schema
                          </Button>
                          <Button variant="danger" onClick={() => void onDelete(source)}
                                  loading={busy === `delete:${source.id}`}>
                            Delete
                          </Button>
                        </div>
                      </td>
                    ) : null}
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

function toError(caught: unknown): { message: string; code?: string } {
  if (caught instanceof ClientApiError) return { message: caught.message, code: caught.code };
  return { message: "The request failed. Please try again." };
}

function Field({
  label, id, value, onChange, type = "text", required = false, placeholder = "", hint = "",
  as = "input", options = [],
}: {
  label: string;
  id: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
  hint?: string;
  as?: "input" | "select";
  options?: string[];
}) {
  const className =
    "w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-ink-900)] placeholder:text-[var(--color-ink-500)]";
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium text-[var(--color-ink-700)]">
        {label}
        {required ? <span className="ml-1 text-[var(--color-danger)]" aria-hidden="true">*</span> : null}
      </label>
      {as === "select" ? (
        <select id={id} value={value} onChange={(event) => onChange(event.target.value)}
                className={className}>
          {options.map((option) => (
            <option key={option} value={option}>{titleCase(option)}</option>
          ))}
        </select>
      ) : (
        <input
          id={id}
          type={type}
          required={required}
          value={value}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          className={className}
        />
      )}
      {hint ? <p className="text-xs text-[var(--color-ink-500)]">{hint}</p> : null}
    </div>
  );
}
