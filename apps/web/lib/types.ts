/**
 * Types mirroring the API response shapes.
 *
 * These are hand-maintained to match `packages/api-contracts/`. If you change a
 * serializer in `apps/api`, update the corresponding contract and this file.
 */

export type Role = "owner" | "admin" | "analyst" | "viewer";

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

export interface Organization {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  role: Role | null;
  member_count: number;
  created_at: string;
}

export interface DataSource {
  id: string;
  name: string;
  description: string;
  engine: "postgresql" | "mysql";
  host: string;
  port: number;
  database_name: string;
  username: string;
  ssl_mode: string;
  is_read_only: boolean;
  status: "unknown" | "connected" | "error";
  last_error: string;
  last_tested_at: string | null;
  last_synced_at: string | null;
  table_count: number;
  created_at: string;
}

export interface DocumentSummary {
  id: string;
  title: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status: "pending" | "processing" | "ready" | "failed";
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
  status: string;
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  duration_ms: number;
  error: string;
}

export interface Execution {
  id: string;
  kind: "analyst_query" | "document_processing";
  status: "pending" | "running" | "succeeded" | "failed";
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

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id?: string | null;
  };
}
