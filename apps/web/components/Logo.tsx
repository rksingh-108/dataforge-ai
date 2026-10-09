export function LogoMark({ className = "h-9 w-9" }: { className?: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-xl bg-[var(--color-brand-500)] shadow-[0_10px_30px_-12px_rgba(224,163,60,0.9)] ${className}`}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true" className="h-1/2 w-1/2 text-[#1a1206]" fill="none">
        <path
          d="M12 2.5 20.5 7v10L12 21.5 3.5 17V7L12 2.5Z"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        <path d="M12 8.2 16.4 10.7v4.6L12 17.8 7.6 15.3v-4.6L12 8.2Z" fill="currentColor" />
      </svg>
    </span>
  );
}
