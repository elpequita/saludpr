"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type SlugMapping = { id: string; slug: string; name: string };

/** Strip accents so "bayamon" matches "Bayamón". */
function fold(s: string): string {
  return s
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

/**
 * Type-ahead search over the 78 municipalities. On phones the choropleth's
 * touch targets are tiny, so this is the primary navigation path there;
 * on desktop it complements clicking the map.
 */
export function MuniSearch() {
  const router = useRouter();
  const [munis, setMunis] = useState<SlugMapping[]>([]);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/municipalities-slugs")
      .then((r) => r.json() as Promise<SlugMapping[]>)
      .then((data) => {
        if (!cancelled) setMunis(data);
      })
      .catch(() => void 0);
    return () => {
      cancelled = true;
    };
  }, []);

  // Close on outside tap
  useEffect(() => {
    const onDown = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, []);

  const matches = useMemo(() => {
    const q = fold(query.trim());
    if (!q) return [];
    return munis.filter((m) => fold(m.name).includes(q)).slice(0, 8);
  }, [query, munis]);

  const go = (slug: string) => {
    setOpen(false);
    router.push(`/municipio/${slug}`);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open || matches.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => (a + 1) % matches.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => (a - 1 + matches.length) % matches.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      go(matches[Math.min(active, matches.length - 1)].slug);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={rootRef} className="relative w-full md:w-72">
      <input
        type="text"
        role="combobox"
        aria-expanded={open && matches.length > 0}
        aria-label="Busca tu municipio"
        placeholder="Busca tu municipio…"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        className="w-full border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-subtle)] focus:border-[var(--color-amber)] focus:outline-none"
      />
      {open && matches.length > 0 && (
        <ul
          role="listbox"
          className="absolute left-0 right-0 top-full z-30 mt-1 border border-[var(--color-border)] bg-[var(--color-surface-elevated)] shadow-2xl"
        >
          {matches.map((m, i) => (
            <li key={m.id} role="option" aria-selected={i === active}>
              <button
                type="button"
                onPointerDown={(e) => {
                  e.preventDefault();
                  go(m.slug);
                }}
                onMouseEnter={() => setActive(i)}
                className={`block w-full px-4 py-2.5 text-left text-sm ${
                  i === active
                    ? "bg-[var(--color-ink-muted)] text-[var(--color-amber-soft)]"
                    : "text-[var(--color-text)]"
                }`}
              >
                {m.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
