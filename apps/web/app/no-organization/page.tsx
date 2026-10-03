import { Card } from "@/components/ui";

export const metadata = { title: "No organization" };

export default function NoOrganizationPage() {
  return (
    <main id="main" className="mx-auto max-w-lg px-4 py-16">
      <Card className="p-6">
        <h1 className="text-lg font-semibold text-[var(--color-ink-900)]">
          You are not a member of an organization yet
        </h1>
        <p className="mt-2 text-sm text-[var(--color-ink-500)]">
          DataForge AI scopes every request to an organization. Ask an existing owner or
          administrator to invite your account, then sign in again.
        </p>
      </Card>
    </main>
  );
}
