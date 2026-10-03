import { SettingsPanel } from "@/components/SettingsPanel";
import { Card, CardHeader, PageHeader } from "@/components/ui";
import { loadSession } from "@/lib/server-session";
import { Permission, hasPermission } from "@/lib/permissions";
import { titleCase } from "@/lib/format";

export const metadata = { title: "Settings" };

export default async function SettingsPage() {
  const { currentUser, membership, memberships } = await loadSession();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Your profile, security settings and organization context."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <SettingsPanel email={currentUser.user.email} fullName={currentUser.user.full_name} />

        <Card>
          <CardHeader title="Organization context" description="Where your requests are scoped." />
          <ul className="divide-y divide-[var(--color-line)]">
            <li className="flex items-center justify-between px-5 py-3 text-sm">
              <span className="text-[var(--color-ink-500)]">Active organization</span>
              <span className="font-medium text-[var(--color-ink-900)]">
                {membership.organization_name}
              </span>
            </li>
            <li className="flex items-center justify-between px-5 py-3 text-sm">
              <span className="text-[var(--color-ink-500)]">Your role</span>
              <span className="font-medium text-[var(--color-ink-900)]">
                {titleCase(membership.role)}
              </span>
            </li>
            <li className="px-5 py-3">
              <p className="text-sm text-[var(--color-ink-500)]">Effective permissions</p>
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {membership.permissions.map((permission) => (
                  <li
                    key={permission}
                    className="rounded border border-[var(--color-line)] bg-[var(--color-canvas)] px-2 py-0.5 text-xs text-[var(--color-ink-700)]"
                  >
                    {permission}
                  </li>
                ))}
              </ul>
            </li>
            <li className="flex items-center justify-between px-5 py-3 text-sm">
              <span className="text-[var(--color-ink-500)]">Memberships</span>
              <span className="font-medium text-[var(--color-ink-900)]">{memberships.length}</span>
            </li>
          </ul>
        </Card>
      </div>

      {hasPermission(membership.permissions, Permission.OrgManage) ? (
        <Card>
          <CardHeader
            title="Organization administration"
            description="Organization settings and audit export are managed by owners and admins."
          />
          <p className="px-5 py-4 text-sm text-[var(--color-ink-500)]">
            Member management lives under Users &amp; Roles. Organization deletion and billing are
            not implemented in this release — see docs/development/known-limitations.md.
          </p>
        </Card>
      ) : null}
    </div>
  );
}
