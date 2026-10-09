"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { Button } from "@/components/Button";
import { Card, CardHeader, EmptyState, ErrorBanner, StatusBadge } from "@/components/ui";
import { ClientApiError, clientFetch } from "@/lib/api-client";
import { formatBytes, formatRelative } from "@/lib/format";
import type { DocumentSummary } from "@/lib/types";

export function DocumentManager({
  organizationId,
  documents,
  canManage,
}: {
  organizationId: string;
  documents: DocumentSummary[];
  canManage: boolean;
}) {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<{ message: string; code?: string } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const base = `/api/v1/orgs/${organizationId}/documents`;

  async function onUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = fileInput.current?.files?.[0];
    if (!file) {
      setError({ message: "Choose a file to upload." });
      return;
    }
    setBusy("upload");
    setError(null);
    setNotice(null);

    const formData = new FormData();
    formData.append("file", file);
    try {
      await clientFetch<DocumentSummary>(`${base}/`, { method: "POST", formData });
      if (fileInput.current) fileInput.current.value = "";
      setNotice("Upload accepted. Processing runs in the background — refresh to see progress.");
      router.refresh();
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(null);
    }
  }

  async function onReprocess(document: DocumentSummary) {
    setBusy(`reprocess:${document.id}`);
    setError(null);
    try {
      await clientFetch(`${base}/${document.id}/reprocess/`, { method: "POST" });
      setNotice("Reprocessing queued.");
      router.refresh();
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(null);
    }
  }

  async function onDelete(document: DocumentSummary) {
    if (!window.confirm(`Delete "${document.title}"? This cannot be undone.`)) return;
    setBusy(`delete:${document.id}`);
    setError(null);
    try {
      await clientFetch(`${base}/${document.id}/`, { method: "DELETE" });
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
        <div role="status" className="rounded-lg border border-emerald-400/25 bg-emerald-400/10 px-4 py-3 text-sm text-[var(--color-ok)]">
          {notice}
        </div>
      ) : null}

      {canManage ? (
        <Card>
          <CardHeader
            title="Upload a document"
            description="Allowed types: PDF, DOCX, TXT. Type, size and file signature are validated."
          />
          <form onSubmit={onUpload} className="flex flex-wrap items-end gap-3 p-5">
            <div className="space-y-1">
              <label htmlFor="file" className="block text-sm font-medium text-[var(--color-ink-700)]">
                File
              </label>
              <input
                id="file"
                ref={fileInput}
                type="file"
                accept=".pdf,.docx,.txt"
                className="block text-sm"
              />
            </div>
            <Button type="submit" loading={busy === "upload"}>
              Upload
            </Button>
          </form>
        </Card>
      ) : null}

      <Card>
        <CardHeader title="Knowledge base" description={`${documents.length} document(s).`} />
        {documents.length === 0 ? (
          <EmptyState
            title="No documents yet"
            description="Upload internal documents so the analyst can cite them when answering questions."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-canvas)] text-left text-xs uppercase tracking-wide text-[var(--color-ink-500)]">
                <tr>
                  <th scope="col" className="px-5 py-2">Title</th>
                  <th scope="col" className="px-5 py-2">Status</th>
                  <th scope="col" className="px-5 py-2">Size</th>
                  <th scope="col" className="px-5 py-2">Chunks</th>
                  <th scope="col" className="px-5 py-2">Uploaded</th>
                  {canManage ? <th scope="col" className="px-5 py-2 text-right">Actions</th> : null}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-line)]">
                {documents.map((document) => (
                  <tr key={document.id}>
                    <td className="px-5 py-3">
                      <p className="font-medium text-[var(--color-ink-900)]">{document.title}</p>
                      <p className="text-xs text-[var(--color-ink-500)]">{document.original_filename}</p>
                      {document.error ? (
                        <p className="mt-1 max-w-sm truncate text-xs text-[var(--color-danger)]"
                           title={document.error}>
                          {document.error}
                        </p>
                      ) : null}
                    </td>
                    <td className="px-5 py-3"><StatusBadge status={document.status} /></td>
                    <td className="px-5 py-3 text-[var(--color-ink-700)]">{formatBytes(document.size_bytes)}</td>
                    <td className="px-5 py-3 text-[var(--color-ink-700)]">{document.chunk_count}</td>
                    <td className="px-5 py-3 text-[var(--color-ink-500)]">{formatRelative(document.created_at)}</td>
                    {canManage ? (
                      <td className="px-5 py-3">
                        <div className="flex justify-end gap-2">
                          {document.status === "failed" ? (
                            <Button variant="secondary"
                                    onClick={() => void onReprocess(document)}
                                    loading={busy === `reprocess:${document.id}`}>
                              Retry
                            </Button>
                          ) : null}
                          <Button variant="danger" onClick={() => void onDelete(document)}
                                  loading={busy === `delete:${document.id}`}>
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
