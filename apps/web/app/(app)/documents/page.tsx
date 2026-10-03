import { DocumentManager } from "@/components/DocumentManager";
import { PageHeader } from "@/components/ui";
import { apiFetch } from "@/lib/api-server";
import { Permission, hasPermission } from "@/lib/permissions";
import { loadSession } from "@/lib/server-session";
import type { DocumentSummary, Paginated } from "@/lib/types";

export const metadata = { title: "Documents" };

export default async function DocumentsPage() {
  const { membership, organizationId } = await loadSession();
  const documents = await apiFetch<Paginated<DocumentSummary>>(
    `/api/v1/orgs/${organizationId}/documents/?page_size=50`,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Documents"
        description="Upload PDF, DOCX or TXT files. Each document goes through real RAG processing: extraction, chunking, embedding and vector storage."
      />
      <DocumentManager
        organizationId={organizationId}
        documents={documents.results}
        canManage={hasPermission(membership.permissions, Permission.DocumentManage)}
      />
    </div>
  );
}
