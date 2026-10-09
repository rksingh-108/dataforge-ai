import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
  as: Tag = "section",
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "article";
}) {
  return (
    <Tag className={`rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] ${className}`}>
      {children}
    </Tag>
  );
}

export function CardHeader({ title, description, actions }: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--color-line)] px-5 py-4">
      <div>
        <h2 className="text-sm font-semibold text-[var(--color-ink-900)]">{title}</h2>
        {description ? (
          <p className="mt-1 text-xs text-[var(--color-ink-500)]">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function PageHeader({ title, description, actions }: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-[var(--color-ink-900)]">{title}</h1>
        {description ? (
          <p className="mt-1 max-w-2xl text-sm text-[var(--color-ink-500)]">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </header>
  );
}

type BadgeTone = "neutral" | "ok" | "warn" | "danger" | "brand";

const TONES: Record<BadgeTone, string> = {
  neutral: "bg-white/5 text-[var(--color-ink-700)] border-white/10",
  ok: "bg-emerald-400/10 text-[var(--color-ok)] border-emerald-400/25",
  warn: "bg-amber-400/10 text-[var(--color-warn)] border-amber-400/25",
  danger: "bg-red-400/10 text-[var(--color-danger)] border-red-400/25",
  brand: "bg-[var(--color-brand-500)]/10 text-[var(--color-brand-300)] border-[var(--color-brand-500)]/25",
};

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: BadgeTone }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

const STATUS_TONES: Record<string, BadgeTone> = {
  succeeded: "ok",
  ready: "ok",
  connected: "ok",
  running: "brand",
  processing: "brand",
  pending: "warn",
  unknown: "neutral",
  failed: "danger",
  error: "danger",
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONES[status] ?? "neutral"}>{status}</Badge>;
}

export function EmptyState({ title, description, action }: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      <p className="text-sm font-medium text-[var(--color-ink-900)]">{title}</p>
      <p className="max-w-md text-xs text-[var(--color-ink-500)]">{description}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

export function ErrorBanner({ message, code }: { message: string; code?: string }) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-red-400/25 bg-red-400/10 px-4 py-3 text-sm text-red-200"
    >
      <p className="font-medium">{message}</p>
      {code ? <p className="mt-1 text-xs opacity-80">Reference: {code}</p> : null}
    </div>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-[var(--color-ink-500)]" role="status">
      <span
        aria-hidden="true"
        className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-line)] border-t-[var(--color-brand-500)]"
      />
      <span>{label}…</span>
    </span>
  );
}

export function SkeletonRows({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2 p-5" aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="h-8 animate-pulse rounded bg-white/5" />
      ))}
    </div>
  );
}

export function StatTile({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Card className="df-hover p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-ink-500)]">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-[var(--color-ink-900)]">{value}</p>
      {hint ? <p className="mt-1 text-xs text-[var(--color-ink-500)]">{hint}</p> : null}
    </Card>
  );
}
