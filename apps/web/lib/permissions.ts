/**
 * Permission constants used for UI gating.
 *
 * IMPORTANT: this file only decides what the UI *shows*. Authorization is
 * enforced server-side (see `docs/architecture/authorization-model.md`). Never
 * treat a hidden button as a security control. The strings mirror
 * `apps/api/apps/common/rbac.py`.
 */
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

export function hasPermission(
  permissions: readonly string[] | undefined,
  permission: PermissionName,
): boolean {
  return Boolean(permissions?.includes(permission));
}

export function hasAny(
  permissions: readonly string[] | undefined,
  required: readonly PermissionName[],
): boolean {
  return required.some((permission) => hasPermission(permissions, permission));
}
