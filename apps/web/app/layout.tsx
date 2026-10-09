import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "DataForge AI",
    template: "%s · DataForge AI",
  },
  description: "Secure AI-powered business data intelligence platform.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <a
          href="#main"
          className="sr-only sr-only-focusable absolute left-2 top-2 z-50 rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)] text-sm"
        >
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
