import { describe, expect, it } from "vitest";

import { Permission, hasAny, hasPermission } from "@/lib/permissions";

const VIEWER = ["org.view", "datasource.view", "document.view", "execution.view"];
const ANALYST = [...VIEWER, "document.manage", "analyst.query"];
const ADMIN = [...ANALYST, "org.manage", "member.manage", "datasource.manage", "audit.view"];

describe("hasPermission", () => {
  it("grants a permission the role has", () => {
    expect(hasPermission(REVIEW(ANALYST), Permission.AnalystQuery)).toBe(true);
  });

  it("denies a permission the role lacks", () => {
    expect(hasPermission(VIEWER, Permission.AnalystQuery)).toBe(false);
  });

  it("denies everything when permissions are missing (fail closed)", () => {
    expect(hasPermission(undefined, Permission.OrgView)).toBe(false);
    expect(hasPermission([], Permission.OrgView)).toBe(false);
  });
});

describe("hasAny", () => {
  it("is true when at least one permission is present", () => {
    expect(hasAny(REVIEW(ANALYST), [Permission.AuditView, Permission.AnalystQuery])).toBe(true);
  });

  it("is false when none are present", () => {
    expect(hasAny(VIEWER, [Permission.AuditView, Permission.MemberManage])).toBe(false);
  });
});

describe("role matrix expectations used by the UI", () => {
  it("viewers cannot query the analyst", () => {
    expect(hasPermission(VIEWER, Permission.AnalystQuery)).toBe(false);
  });

  it("admins can view audit logs", () => {
    expect(hasPermission(ADMIN, Permission.AuditView)).toBe(true);
  });
});

function REVIEW(permissions: string[]): string[] {
  return permissions;
}
