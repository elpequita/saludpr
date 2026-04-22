"use client";

import { Suspense, useEffect, useState } from "react";
import { PRMap } from "@/components/pr-map";
import { IndicatorPicker } from "@/components/indicator-picker";
import { BarrioDrilldownHeader } from "@/components/barrio-drilldown-header";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { TerritoryContextPanel } from "@/components/territory-context-panel";
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
      <SiteHeader />

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

      <TerritoryContextPanel />

      <SiteFooter />
    </main>
  );
}
