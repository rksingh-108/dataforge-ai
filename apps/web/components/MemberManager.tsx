"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/Button";
import { Badge, Card, CardHeader, EmptyState, ErrorBanner } from "@/components/ui";
import { ClientApiError, clientFetch } from "@/lib/api-client";
import { Permission, hasPermission } from "@/lib/permissions";
import { formatRelative, titleCase } from "@/lib/format";

interface MembershipRow {
  id: string;
  user: string;
  user_email: string;
  user_name: string;
  role: string;
  is_active: boolean;
  permissions: string[];
  created_at: string;
}

const ROLES = ["owner", "admin", "analyst", "viewer"] as const;

export function MemberManager({
  organizationId,
  members,
  currentUserId,
  myPermissions,
}: {
  organizationId: string;
  members: MembershipRow[];
  currentUserId: string;
  myPermissions: readonly string[];
}) {
  const router = useRouter();
  const canManage = hasPermission(myPermissions, Permission.MemberManage);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<string>("analyst");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<{ message: string; code?: string } | null>(null);

  const base = `/api/v1/orgs/${organizationId}/members`;

  async function onInvite(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("invite");
    setError(null);
    try {
      await clientFetch(`${base}/`, { method: "POST", body: { email, role } });
      setEmail("");
      router.refresh();
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(null);
    }
  }

  async function onChangeRole(member: MembershipRow, nextRole: string) {
    setBusy(`role:${member.id}`);
    setError(null);
    try {
      await clientFetch(`${base}/${member.id}/`, { method: "PATCH", body: { role: nextRole } });
      router.refresh();
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(null);
    }
  }

  async function onRemove(member: MembershipRow) {
    if (!window.confirm(`Remove ${member.user_email} from this organization?`)) return;
    setBusy(`remove:${member.id}`);
    setError(null);
    try {
      await clientFetch(`${base}/${member.id}/`, { method: "DELETE" });
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

      {canManage ? (
        <Card>
          <CardHeader
            title="Add a member"
            description="The user must already have a DataForge account. They gain access immediately."
          />
          <form onSubmit={onInvite} className="flex flex-wrap items-end gap-3 p-5">
            <div className="space-y-1">
              <label htmlFor="member-email" className="block text-sm font-medium text-[var(--color-ink-700)]">
                Email
              </label>
              <input
                id="member-email"
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-64 rounded-md border border-[var(--color-line)] px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="member-role" className="block text-sm font-medium text-[var(--color-ink-700)]">
                Role
              </label>
              <select
                id="member-role"
                value={role}
                onChange={(event) => setRole(event.target.value)}
                className="rounded-md border border-[var(--color-line)] px-3 py-2 text-sm"
              >
                {ROLES.map((value) => (
                  <option key={value} value={value}>{titleCase(value)}</option>
                ))}
              </select>
            </div>
            <Button type="submit" loading={busy === "invite"}>Add member</Button>
          </form>
        </Card>
      ) : null}

      <Card>
        <CardHeader title="Members" description={`${members.length} member(s) in this organization.`} />
        {members.length === 0 ? (
          <EmptyState title="No members" description="This should not happen — every organization has an owner." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-canvas)] text-left text-xs uppercase tracking-wide text-[var(--color-ink-500)]">
                <tr>
                  <th scope="col" className="px-5 py-2">Member</th>
                  <th scope="col" className="px-5 py-2">Role</th>
                  <th scope="col" className="px-5 py-2">Status</th>
                  <th scope="col" className="px-5 py-2">Joined</th>
                  {canManage ? <th scope="col" className="px-5 py-2 text-right">Actions</th> : null}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-line)]">
                {members.map((member) => {
                  const isSelf = member.user === currentUserId;
                  return (
                    <tr key={member.id}>
                      <td className="px-5 py-3">
                        <p className="font-medium text-[var(--color-ink-900)]">
                          {member.user_name || member.user_email}
                          {isSelf ? <span className="ml-2 text-xs text-[var(--color-ink-500)]">(you)</span> : null}
                        </p>
                        <p className="text-xs text-[var(--color-ink-500)]">{member.user_email}</p>
                      </td>
                      <td className="px-5 py-3">
                        {canManage && !isSelf ? (
                          <select
                            aria-label={`Role for ${member.user_email}`}
                            value={member.role}
                            disabled={busy === `role:${member.id}`}
                            onChange={(event) => void onChangeRole(member, event.target.value)}
                            className="rounded-md border border-[var(--color-line)] px-2 py-1 text-sm"
                          >
                            {ROLES.map((value) => (
                              <option key={value} value={value}>{titleCase(value)}</option>
                            ))}
                          </select>
                        ) : (
                          <Badge tone="brand">{titleCase(member.role)}</Badge>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <Badge tone={member.is_active ? "ok" : "neutral"}>
                          {member.is_active ? "active" : "inactive"}
                        </Badge>
                      </td>
                      <td className="px-5 py-3 text-[var(--color-ink-500)]">
                        {formatRelative(member.created_at)}
                      </td>
                      {canManage ? (
                        <td className="px-5 py-3 text-right">
                          {!isSelf && member.is_active ? (
                            <Button variant="danger" onClick={() => void onRemove(member)}
                                    loading={busy === `remove:${member.id}`}>
                              Remove
                            </Button>
                          ) : null}
                        </td>
                      ) : null}
                    </tr>
                  );
                })}
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
