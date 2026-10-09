import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";
type Size = "sm" | "md" | "lg";

const SIZES: Record<Size, string> = {
  sm: "px-2.5 py-1 text-xs",
  md: "px-3 py-1.5 text-sm",
  lg: "px-4 py-2.5 text-sm",
};

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-[var(--color-brand-500)] text-[#1a1206] hover:bg-[var(--color-brand-400)] shadow-[0_10px_30px_-14px_rgba(224,163,60,0.9)] disabled:bg-white/10 disabled:text-white/40 disabled:shadow-none",
  secondary:
    "border border-[var(--color-line)] bg-white/5 text-[var(--color-ink-700)] hover:bg-white/10 hover:text-[var(--color-ink-900)]",
  danger: "bg-red-500/90 text-white hover:bg-red-500",
  ghost: "text-[var(--color-ink-700)] hover:bg-white/5 hover:text-[var(--color-ink-900)]",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  children,
  className = "",
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition disabled:cursor-not-allowed disabled:opacity-70 ${SIZES[size]} ${VARIANTS[variant]} ${className}`}
    >
      {loading ? (
        <span
          aria-hidden="true"
          className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white"
        />
      ) : null}
      {children}
    </button>
  );
}
