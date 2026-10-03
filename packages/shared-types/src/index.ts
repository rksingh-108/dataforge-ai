/**
 * @dataforge/shared-types
 *
 * TypeScript mirrors of the API response shapes.
 *
 * These types describe **wire formats**, not domain rules. They are deliberately
 * structural: no classes, no behaviour, nothing that could be mistaken for
 * business logic. If a rule is needed, it belongs in `apps/api`.
 *
 * When the API changes a serializer, update:
 *   1. this file,
 *   2. `apps/web/lib/types.ts` (which re-exports for page convenience),
 *   3. `packages/api-contracts/` if the change crosses the AI-service boundary.
 */

export type Role = "owner" | "admin" | "analyst" | "viewer";

export type ExecutionStatus = "pending" | "running" | "succeeded" | "failed";
export type ExecutionKind = "analyst_query" | "document_processing";
export type DocumentStatus = "pending" | "processing" | "ready" | "failed";
export type DataSourceStatus = "unknown" | "connected" | "error";
export type DataSourceEngine = "postgresql" | "mysql";
export type ToolStatus = "pending" | "running" | "succeeded" | "failed";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  date_joined: string;
}

export interface MembershipSummary {
  organization_id: string;
  organization_name: string;
  organization_slug: string;
  role: Role;
  permissions: string[];
}

export interface CurrentUser {
  user: User;
  memberships: MembershipSummary[];
  is_staff: boolean;
}

export interface Membership {
  id: string;
  user: string;
  user_email: string;
  user_name: string;
  role: Role;
  is_active: boolean;
  permissions: string[];
  created_at: string;
}

export interface DataSource {
  id: string;
  name: string;
  description: string;
  engine: DataSourceEngine;
  host: string;
  port: number;
  database_name: string;
  username: string;
  ssl_mode: string;
  is_read_only: boolean;
  status: DataSourceStatus;
  last_error: string;
  last_tested_at: string | null;
  last_synced_at: string | null;
  table_count: number;
  created_at: string;
}

export interface SchemaColumn {
  column_name: string;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
}

export interface SchemaTable {
  id: string;
  schema_name: string;
  table_name: string;
  row_estimate: number | null;
  columns: SchemaColumn[];
}

export interface DocumentSummary {
  id: string;
  title: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status: DocumentStatus;
  error: string;
  page_count: number;
  chunk_count: number;
  uploaded_by_email: string | null;
  processed_at: string | null;
  created_at: string;
}

export interface ExecutionStep {
  id: string;
  index: number;
  tool_name: string;
  title: string;
  status: ToolStatus;
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  duration_ms: number;
  error: string;
}

export interface Execution {
  id: string;
  kind: ExecutionKind;
  status: ExecutionStatus;
  question: string;
  answer: string;
  error: string;
  user_email: string | null;
  datasource_name: string | null;
  document_title: string | null;
  provider: string;
  model_name: string;
  total_tokens: number;
  duration_ms: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  steps?: ExecutionStep[];
}

export interface AuditLogEntry {
  id: string;
  action: string;
  actor_email: string | null;
  target_type: string;
  target_id: string;
  metadata: Record<string, unknown>;
  ip_address: string | null;
  request_id: string;
  created_at: string;
}

export interface Insights {
  executions: {
    total: number;
    succeeded: number;
    failed: number;
    running: number;
    success_rate_percent: number;
  };
  top_tools: { tool: string; count: number }[];
}

export interface Paginated<T> {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: T[];
}

/** The single error envelope returned by every failing endpoint. */
export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id?: string | null;
  };
}

/** Permissions, mirroring `apps/api/apps/common/rbac.py`. */
export const Permission = {
  OrgView: "org.view",
  OrgManage: "org.manage",
  MemberManage: "member.manage",
  DatasourceView: "datasource.view",
  DatasourceManage: "datasource.manage",
  DocumentView: "document.view",
  DocumentManage: "document.manage",
  AnalystQuery: "analyst.query",
  ExecutionView: "execution.view",
  AuditView: "audit.view",
} as const;

export type PermissionName = (typeof Permission)[keyof typeof Permission];
