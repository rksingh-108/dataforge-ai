import { redirect } from "next/navigation";

import { LoginForm } from "@/components/LoginForm";
import { LogoMark } from "@/components/Logo";
import { getAccessToken } from "@/lib/session";

export const metadata = { title: "Sign in" };

const FEATURES = [
  "Read-only SQL over every connected database",
  "Answers grounded in your documents, with citations",
  "Every AI run recorded in a tamper-evident audit log",
];

function CheckIcon() {
  return (
    <svg
      viewBox="0 0 20 20"
      aria-hidden="true"
      className="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-brand-400)]"
      fill="none"
    >
      <circle cx="10" cy="10" r="8.25" stroke="currentColor" strokeWidth="1.5" className="opacity-40" />
      <path
        d="m6.4 10.2 2.4 2.4 4.8-5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default async function LoginPage() {
  if (await getAccessToken()) {
    redirect("/dashboard");
  }

  return (
    <main id="main" className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel — animated, editorial, hidden on small screens. */}
      <section className="relative hidden flex-col justify-between overflow-hidden bg-[#08080a] p-10 lg:flex xl:p-14">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage:
              "linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)",
            backgroundSize: "46px 46px",
          }}
        />
        <div
          aria-hidden="true"
          className="df-glow pointer-events-none absolute -left-24 -top-24 h-96 w-96 rounded-full bg-[var(--color-brand-500)] opacity-30 blur-[120px]"
        />
        <div
          aria-hidden="true"
          className="df-float pointer-events-none absolute -bottom-24 -right-20 h-96 w-96 rounded-full bg-[var(--color-brand-600)] opacity-20 blur-[120px]"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_100%_at_50%_50%,transparent_40%,rgba(0,0,0,0.55)_100%)]"
        />

        <div className="df-reveal relative flex items-center gap-3">
          <LogoMark />
          <div>
            <p className="text-sm font-semibold tracking-tight">DataForge AI</p>
            <p className="text-xs text-white/60">Business data intelligence</p>
          </div>
        </div>

        <div className="relative max-w-md">
          <p className="df-reveal df-delay-1 text-xs font-semibold uppercase tracking-[0.28em] text-[var(--color-brand-400)]">
            Secure workspace
          </p>
          <h2 className="df-reveal df-delay-2 mt-5 font-display text-4xl font-medium leading-[1.1] tracking-tight xl:text-5xl">
            <span className="text-[var(--color-ink-900)]">Ask your business data anything.</span>{" "}
            <span className="text-[var(--color-brand-400)]">Get answers you can defend.</span>
          </h2>
          <p className="df-reveal df-delay-3 mt-5 text-sm leading-relaxed text-white/65">
            DataForge answers with read-only SQL over your connected databases and cites the
            documents behind every result.
          </p>
          <ul className="mt-8 space-y-3.5">
            {FEATURES.map((feature, index) => (
              <li
                key={feature}
                className={`df-reveal df-delay-${index + 3} flex items-start gap-3 text-sm text-white/85`}
              >
                <CheckIcon />
                <span>{feature}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="df-reveal df-delay-5 relative text-xs text-white/45">
          Access is scoped to your organization and role. Every AI run is audited.
        </p>
      </section>

      {/* Form panel */}
      <section className="relative flex items-center justify-center px-4 py-12 sm:px-8 lg:border-l lg:border-white/5">
        <div className="w-full max-w-sm">
          <div className="df-reveal mb-8 flex items-center gap-3 lg:hidden">
            <LogoMark className="h-9 w-9" />
            <div>
              <p className="text-sm font-semibold tracking-tight text-[var(--color-ink-900)]">
                DataForge AI
              </p>
              <p className="text-xs text-[var(--color-ink-500)]">Business data intelligence</p>
            </div>
          </div>

          <p className="df-reveal text-xs font-semibold uppercase tracking-[0.28em] text-[var(--color-brand-400)]">
            Sign in
          </p>
          <h1 className="df-reveal df-delay-1 mt-3 font-display text-3xl font-medium tracking-tight text-[var(--color-ink-900)]">
            Welcome back
          </h1>
          <p className="df-reveal df-delay-2 mt-2 text-sm text-[var(--color-ink-500)]">
            Use your organization credentials to continue.
          </p>

          <div className="df-reveal df-delay-3 df-hover relative mt-7 overflow-hidden rounded-2xl border border-white/10 bg-[var(--color-surface)]/80 p-6 shadow-[0_40px_90px_-50px_rgba(0,0,0,0.95)] backdrop-blur-xl sm:p-7">
            <span aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-[var(--color-brand-500)]/40" />
            <LoginForm />
          </div>

          <p className="df-reveal df-delay-4 mt-6 text-center text-xs text-[var(--color-ink-500)]">
            Trouble signing in? Contact your workspace owner.
          </p>
        </div>
      </section>
    </main>
  );
}
