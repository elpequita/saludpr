"use client";

import { Suspense, useEffect, useState } from "react";
import { PRMap } from "@/components/pr-map";
import { IndicatorPicker } from "@/components/indicator-picker";
import { BarrioDrilldownHeader } from "@/components/barrio-drilldown-header";
import { INDICATORS } from "@/lib/indicators";

type IndicatorApiRow = {
  code: string;
  value_type: string;
  source_slug: string;
  source_name: string;
  years: number[];
  total_rows: number;
};

const DEFAULT_INDICATOR = "pct_below_poverty";

export default function HomePage() {
  const [indicators, setIndicators] = useState<IndicatorApiRow[]>([]);
  const [selected, setSelected] = useState<string>(DEFAULT_INDICATOR);
  const [year, setYear] = useState<number>(2023);
  const [breaks, setBreaks] = useState<number[] | null>(null);
  const [selectedMuniName, setSelectedMuniName] = useState<string | null>(null);

  // Fetch list of available indicators
  useEffect(() => {
    let cancelled = false;
    fetch("/api/metrics/indicators")
      .then((r) => r.json() as Promise<IndicatorApiRow[]>)
      .then((data) => {
        if (cancelled) return;
        setIndicators(data);
        // Pick default year = latest available for default indicator
        const defaultInd = data.find((d) => d.code === DEFAULT_INDICATOR);
        if (defaultInd && defaultInd.years.length > 0) {
          setYear(Math.max(...defaultInd.years));
        }
      })
      .catch(() => void 0);
    return () => {
      cancelled = true;
    };
  }, []);

  // When indicator changes, snap year to latest available for it
  const handleIndicatorChange = (code: string) => {
    setSelected(code);
    const match = indicators.find((d) => d.code === code);
    if (match && match.years.length > 0) {
      setYear(Math.max(...match.years));
    }
  };

  const availableYears =
    indicators.find((d) => d.code === selected)?.years ?? [year];
  const availableIndicatorCodes = indicators
    .map((d) => d.code)
    .filter((c) => INDICATORS[c] !== undefined);

  return (
    <main className="relative z-10 min-h-screen">
      {/* Header */}
      <header className="border-b border-[var(--color-border)] bg-[var(--color-ink)]/70 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3 rise rise-1">
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
          </div>

          <nav className="flex items-center gap-8 text-sm text-[var(--color-text-muted)] rise rise-2">
            <a href="#about" className="transition-colors hover:text-[var(--color-text)]">
              Acerca
            </a>
            <a
              href="#methodology"
              className="transition-colors hover:text-[var(--color-text)]"
            >
              Metodología
            </a>
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

      {/* Hero */}
      <section className="mx-auto max-w-7xl px-6 pb-12 pt-16 md:pt-24">
        <div className="grid gap-12 md:grid-cols-[1.1fr_1fr] md:items-end">
          <div>
            <p className="mb-5 font-mono text-xs uppercase tracking-[0.3em] text-[var(--color-teal-soft)] rise rise-1">
              Panel público · v0.1
            </p>
            <h1 className="font-display text-5xl leading-[1.02] tracking-tight text-[var(--color-text)] md:text-7xl rise rise-2">
              Los datos de salud
              <br />
              <span className="italic text-[var(--color-amber-soft)]">
                que faltaban
              </span>
              <br />
              en Puerto Rico.
            </h1>
          </div>

          <div className="max-w-md text-lg leading-relaxed text-[var(--color-text-muted)] rise rise-3">
            <p>
              Un mapa público, bilingüe y gratuito que muestra determinantes
              sociales de la salud en los{" "}
              <span className="text-[var(--color-text)]">78 municipios</span> de
              la isla. Cada número es rastreable a su fuente pública.
            </p>
          </div>
        </div>
      </section>

      {/* Map section */}
      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-4 flex items-end justify-between rise rise-4">
          <div>
            <h2 className="font-display text-3xl tracking-tight md:text-4xl">
              El mapa
            </h2>
            <p className="mt-1 font-mono text-xs uppercase tracking-widest text-[var(--color-text-subtle)]">
              Fuente: US Census ACS / PR Community Survey
            </p>
          </div>
          <p className="hidden text-xs text-[var(--color-text-muted)] md:block">
            Haz clic en un municipio para ver detalles
          </p>
        </div>

        <div className="space-y-0 rise rise-5">
          <IndicatorPicker
            indicator={selected}
            year={year}
            availableIndicators={availableIndicatorCodes}
            availableYears={availableYears}
            breaks={breaks}
            onIndicatorChange={handleIndicatorChange}
            onYearChange={setYear}
          />
          <div className="overflow-hidden border border-t-0 border-[var(--color-border)] shadow-2xl">
            {selectedMuniName && (
              <BarrioDrilldownHeader
                muniName={selectedMuniName}
                barrioCount={null}
              />
            )}
            <Suspense
              fallback={
                <div className="flex h-[560px] items-center justify-center bg-[var(--color-surface)]">
                  <div className="font-mono text-xs uppercase tracking-widest text-[var(--color-teal-soft)]">
                    Preparando mapa…
                  </div>
                </div>
              }
            >
              <PRMap
                indicator={selected}
                year={year}
                onBreaksComputed={setBreaks}
                onMuniSelected={setSelectedMuniName}
              />
            </Suspense>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-12 border-t border-[var(--color-border)] bg-[var(--color-ink-soft)]/50">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-8 text-sm text-[var(--color-text-muted)] md:flex-row md:items-center md:justify-between">
          <div>
            Un proyecto de{" "}
            <a
              href="https://www.dataurea.com"
              target="_blank"
              rel="noreferrer"
              className="text-[var(--color-amber)] underline-offset-4 hover:underline"
            >
              Dataurea
            </a>{" "}
            · Datos bajo{" "}
            <a
              href="https://creativecommons.org/licenses/by/4.0/"
              target="_blank"
              rel="noreferrer"
              className="underline-offset-4 hover:underline"
            >
              CC BY 4.0
            </a>
          </div>
          <div className="font-mono text-xs uppercase tracking-widest">
            PR · EN / ES
          </div>
        </div>
      </footer>
    </main>
  );
}
