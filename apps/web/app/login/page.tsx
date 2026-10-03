import { redirect } from "next/navigation";

import { LoginForm } from "@/components/LoginForm";
import { Card } from "@/components/ui";
import { getAccessToken } from "@/lib/session";

export const metadata = { title: "Sign in" };

export default async function LoginPage() {
  if (await getAccessToken()) {
    redirect("/dashboard");
  }

  return (
    <main id="main" className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-brand-600)]">
            DataForge AI
          </p>
          <h1 className="mt-2 text-xl font-semibold text-[var(--color-ink-900)]">
            Sign in to your workspace
          </h1>
          <p className="mt-1 text-sm text-[var(--color-ink-500)]">
            Use your organization credentials.
          </p>
        </div>
        <Card className="p-6">
          <LoginForm />
        </Card>
        <p className="mt-4 text-center text-xs text-[var(--color-ink-500)]">
          Access is scoped to your organization and role. Every AI run is audited.
        </p>
      </div>
    </main>
  );
}
