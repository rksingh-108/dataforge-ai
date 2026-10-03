"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Permission, hasPermission } from "@/lib/permissions";

interface NavItem {
  href: string;
  label: string;
  permission?: (typeof Permission)[keyof typeof Permission];
  description: string;
}

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", description: "Overview and recent activity" },
  {
    href: "/analyst",
    label: "AI Analyst",
    permission: Permission.AnalystQuery,
    description: "Ask questions of your data",
  },
  {
    href: "/data-sources",
    label: "Data Sources",
    permission: Permission.DatasourceView,
    description: "Connected business databases",
  },
  {
    href: "/documents",
    label: "Documents",
    permission: Permission.DocumentView,
    description: "Uploaded knowledge base",
  },
  {
    href: "/executions",
    label: "Executions",
    permission: Permission.ExecutionView,
    description: "AI run history",
  },
  {
    href: "/audit",
    label: "Audit Logs",
    permission: Permission.AuditView,
    description: "Security-relevant events",
  },
  {
    href: "/members",
    label: "Users & Roles",
    permission: Permission.MemberManage,
    description: "Organization membership",
  },
  { href: "/settings", label: "Settings", description: "Your profile and session" },
];

export function Sidebar({ permissions }: { permissions: readonly string[] }) {
  const pathname = usePathname();
  const visible = NAV.filter(
    (item) => !item.permission || hasPermission(permissions, item.permission),
  );

  return (
    <nav aria-label="Main navigation" className="flex flex-col gap-1 p-3">
      {visible.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            title={item.description}
            className={`rounded-md px-3 py-2 text-sm font-medium transition ${
              active
                ? "bg-[var(--color-brand-50)] text-[var(--color-brand-700)]"
                : "text-[var(--color-ink-700)] hover:bg-slate-100"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
