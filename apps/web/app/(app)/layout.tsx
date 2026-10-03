import Link from "next/link";

import { LogoutButton } from "@/components/LogoutButton";
import { OrgSwitcher } from "@/components/OrgSwitcher";
import { Sidebar } from "@/components/Sidebar";
import { Badge } from "@/components/ui";
import { titleCase } from "@/lib/format";
import { loadSession } from "@/lib/server-session";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const { currentUser, membership, memberships, organizationId } = await loadSession();

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-[var(--color-line)] bg-white md:flex">
        <div className="border-b border-[var(--color-line)] px-4 py-4">
          <Link href="/dashboard" className="block">
            <span className="text-sm font-semibold tracking-tight text-[var(--color-ink-900)]">
              DataForge AI
            </span>
            <span className="mt-0.5 block text-xs text-[var(--color-ink-500)]">
              Business data intelligence
            </span>
          </Link>
        </div>

        <OrgSwitcher memberships={memberships} activeId={organizationId} />

        <div className="flex-1 overflow-y-auto">
          <Sidebar permissions={membership.permissions} />
        </div>

        <div className="space-y-3 border-t border-[var(--color-line)] p-3">
          <div>
            <p className="truncate text-sm font-medium text-[var(--color-ink-900)]">
              {currentUser.user.full_name || currentUser.user.email}
            </p>
            <p className="truncate text-xs text-[var(--color-ink-500)]">{currentUser.user.email}</p>
            <div className="mt-2">
              <Badge tone="brand">{titleCase(membership.role)}</Badge>
            </div>
          </div>
          <LogoutButton />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-[var(--color-line)] bg-white px-4 py-3 md:hidden">
          <span className="text-sm font-semibold">DataForge AI</span>
          <span className="text-xs text-[var(--color-ink-500)]">{membership.organization_name}</span>
        </header>
        <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 md:px-6 md:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
