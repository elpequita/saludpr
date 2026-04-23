"use client";

import { INDICATORS, formatValue } from "@/lib/indicators";

type IndicatorYearValue = {
  year: number;
  value: number | null;
};

type MuniIndicatorSeries = {
  code: string;
  value_type: string | null;
  values: IndicatorYearValue[];
  latest_year: number | null;
  latest_value: number | null;
  source_slug: string | null;
};

type Props = {
  indicators: MuniIndicatorSeries[];
};

/** Tiny sparkline, matches the territory panel pattern. */
function Sparkline({ values }: { values: IndicatorYearValue[] }) {
  const numeric = values.filter(
    (v): v is { year: number; value: number } => v.value !== null,
  );
  if (numeric.length < 2) {
    return (
      <div className="font-mono text-[9px] uppercase tracking-[0.15em] text-[var(--color-text-subtle)]">
        serie incompleta
      </div>
    );
  }

  const width = 100;
  const height = 24;
  const pad = 2;
  const xs = numeric.map(
    (_, i) => pad + (i * (width - pad * 2)) / (numeric.length - 1),
  );
  const minV = Math.min(...numeric.map((n) => n.value));
  const maxV = Math.max(...numeric.map((n) => n.value));
  const range = Math.max(maxV - minV, 0.001);
  const ys = numeric.map(
    (n) => height - pad - ((n.value - minV) / range) * (height - pad * 2),
  );
  const points = xs.map((x, i) => `${x},${ys[i]}`).join(" ");
  const lastX = xs[xs.length - 1];
  const lastY = ys[ys.length - 1];

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={lastX} cy={lastY} r="2" fill="currentColor" />
    </svg>
  );
}

function IndicatorCard({ series }: { series: MuniIndicatorSeries }) {
  const meta = INDICATORS[series.code];
  const label = meta?.label_es ?? series.code;
  const unit = meta?.unit ?? "count";
  const direction = meta?.direction ?? "neutral";

  const toneClass =
    direction === "high_is_bad"
      ? "text-[var(--color-amber)]"
      : direction === "high_is_good"
      ? "text-[var(--color-teal-soft)]"
      : direction === "low_is_bad"
      ? "text-[var(--color-amber-soft)]"
      : "text-[var(--color-text)]";

  return (
    <div className="flex flex-col gap-3 border border-[var(--color-border)] bg-[var(--color-surface)]/40 p-5">
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-text-subtle)]">
          {meta?.short_es ?? series.code}
        </span>
        {series.latest_year !== null && (
          <span className="font-mono text-[10px] text-[var(--color-text-subtle)]">
            {series.latest_year}
          </span>
        )}
      </div>

      <div className={`font-display text-3xl leading-none ${toneClass}`}>
        {series.latest_value !== null
          ? formatValue(series.latest_value, unit)
          : "—"}
      </div>

      <p className="text-[12px] leading-snug text-[var(--color-text-muted)]">
        {label}
      </p>

      <div className={`${toneClass} mt-auto`}>
        <Sparkline values={series.values} />
      </div>
    </div>
  );
}

export function MuniSdohGrid({ indicators }: Props) {
  return (
    <section id="sdoh" className="mx-auto max-w-5xl px-6 py-16">
      <div className="mb-6">
        <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-[var(--color-teal-soft)]">
          Determinantes sociales de la salud
        </div>
        <h2 className="mt-2 font-display text-3xl tracking-tight md:text-4xl">
          Los números
        </h2>
        <p className="mt-2 text-sm text-[var(--color-text-muted)]">
          Fuente: US Census ACS / PR Community Survey · 5-year estimates
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
        {indicators.map((ind) => (
          <IndicatorCard key={ind.code} series={ind} />
        ))}
      </div>
    </section>
  );
}
