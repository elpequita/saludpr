"use client";

import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b border-[var(--color-border)] bg-[var(--color-ink)]/70 backdrop-blur-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <Link
          href="/"
          className="flex items-center gap-3 rise rise-1 transition-opacity hover:opacity-80"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-sm bg-[var(--color-amber)] text-[var(--color-ink)]">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-4 w-4"
              aria-hidden="true"
            >
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
            </svg>
          </div>
          <span className="font-display text-xl leading-none tracking-tight">
            Salud<span className="text-[var(--color-amber)]">PR</span>
          </span>
        </Link>

        <nav className="flex items-center gap-8 text-sm text-[var(--color-text-muted)] rise rise-2">
          <Link
            href="/acerca"
            className="transition-colors hover:text-[var(--color-text)]"
          >
            Acerca
          </Link>
          <Link
            href="/metodologia"
            className="transition-colors hover:text-[var(--color-text)]"
          >
            Metodología
          </Link>
          <a
            href="https://www.dataurea.com"
            target="_blank"
            rel="noreferrer"
            className="transition-colors hover:text-[var(--color-text)]"
          >
            Dataurea ↗
          </a>
        </nav>
      </div>
    </header>
  );
}
