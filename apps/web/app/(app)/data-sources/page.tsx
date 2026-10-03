import { DataSourceManager } from "@/components/DataSourceManager";
import { PageHeader } from "@/components/ui";
import { apiFetch } from "@/lib/api-server";
import { Permission, hasPermission } from "@/lib/permissions";
import { loadSession } from "@/lib/server-session";
import type { DataSource, Paginated } from "@/lib/types";

export const metadata = { title: "Data Sources" };

export default async function DataSourcesPage() {
  const { membership, organizationId } = await loadSession();
  const datasources = await apiFetch<Paginated<DataSource>>(
    `/api/v1/orgs/${organizationId}/datasources/?page_size=100`,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Data Sources"
        description="Connect approved business databases. Connections are read-only by default and credentials are encrypted at rest — passwords are never returned to the browser."
      />
      <DataSourceManager
        organizationId={organizationId}
        datasources={datasources.results}
        canManage={hasPermission(membership.permissions, Permission.DatasourceManage)}
      />
    </div>
  );
}
