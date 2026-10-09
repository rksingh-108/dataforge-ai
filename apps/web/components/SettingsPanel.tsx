"use client";

import { useState } from "react";

import { Button } from "@/components/Button";
import { Card, CardHeader, ErrorBanner } from "@/components/ui";
import { ClientApiError, clientFetch } from "@/lib/api-client";

export function SettingsPanel({ email, fullName }: { email: string; fullName: string }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; code?: string } | null>(null);
  const [done, setDone] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      await clientFetch("/api/v1/auth/password/change/", {
        method: "POST",
        body: { current_password: currentPassword, new_password: newPassword },
      });
      setCurrentPassword("");
      setNewPassword("");
      setDone(true);
    } catch (caught) {
      if (caught instanceof ClientApiError) setError({ message: caught.message, code: caught.code });
      else setError({ message: "The password could not be changed." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Profile"
        description="Your account details and password. Changing your password signs out other sessions."
      />
      <div className="space-y-4 p-5">
        <dl className="grid gap-3 sm:grid-cols-2">
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--color-ink-500)]">Email</dt>
            <dd className="text-sm text-[var(--color-ink-900)]">{email}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--color-ink-500)]">Name</dt>
            <dd className="text-sm text-[var(--color-ink-900)]">{fullName || "—"}</dd>
          </div>
        </dl>

        <form onSubmit={onSubmit} className="space-y-3 border-t border-[var(--color-line)] pt-4">
          {error ? <ErrorBanner message={error.message} code={error.code} /> : null}
          {done ? (
            <div role="status" className="rounded-lg border border-emerald-400/25 bg-emerald-400/10 px-4 py-3 text-sm text-[var(--color-ok)]">
              Password changed. Other sessions have been signed out.
            </div>
          ) : null}

          <div className="space-y-1">
            <label htmlFor="current_password" className="block text-sm font-medium text-[var(--color-ink-700)]">
              Current password
            </label>
            <input
              id="current_password"
              type="password"
              autoComplete="current-password"
              required
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-ink-900)] placeholder:text-[var(--color-ink-500)]"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="new_password" className="block text-sm font-medium text-[var(--color-ink-700)]">
              New password
            </label>
            <input
              id="new_password"
              type="password"
              autoComplete="new-password"
              required
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-ink-900)] placeholder:text-[var(--color-ink-500)]"
            />
            <p className="text-xs text-[var(--color-ink-500)]">
              At least 10 characters and not a commonly used password.
            </p>
          </div>
          <Button type="submit" loading={busy}>Change password</Button>
        </form>
      </div>
    </Card>
  );
}
