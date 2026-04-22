"use client";

import { useEffect, useState } from "react";

type TerritoryIndicatorRow = {
  code: string;
  latest_year: number;
  latest_value: number | null;
  source_slug: string;
  source_name: string;
  year_count: number;
};

type TerritoryValue = {
  year: number;
  value: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
  sample_size: number | null;
  is_suppressed: boolean;
};

type TerritoryTrend = {
  indicator_code: string;
  values: TerritoryValue[];
};

// --- Human-readable indicator metadata ---
type IndicatorDisplay = {
  label: string;
  shortLabel: string;
  caption: string;
  severity: "alert" | "warning" | "neutral";
};

const DISPLAY: Record<string, IndicatorDisplay> = {
  pct_diabetes_diagnosed: {
    label: "Diabetes diagnosticada",
    shortLabel: "Diabetes",
    caption: "Adultos que un médico les ha dicho que tienen diabetes",
    severity: "alert",
  },
  pct_hypertension: {
    label: "Presión alta diagnosticada",
    shortLabel: "Hipertensión",
    caption: "Adultos diagnosticados con presión alta",
    severity: "alert",
  },
  pct_obesity: {
    label: "Obesidad (BMI ≥ 30)",
    shortLabel: "Obesidad",
    caption: "Adultos con índice de masa corporal ≥ 30",
    severity: "warning",
  },
  pct_current_asthma: {
    label: "Asma actual",
    shortLabel: "Asma",
    caption: "Adultos que actualmente tienen asma",
    severity: "warning",
  },
  pct_copd: {
    label: "EPOC",
    shortLabel: "EPOC",
    caption: "Adultos diagnosticados con EPOC",
    severity: "warning",
  },
  pct_depression_ever: {
    label: "Depresión diagnosticada",
    shortLabel: "Depresión",
    caption: "Adultos diagnosticados con depresión alguna vez",
    severity: "alert",
  },
  pct_chd_or_mi: {
    label: "Enfermedad coronaria",
    shortLabel: "Corazón",
    caption: "Adultos con enfermedad coronaria o ataque al corazón",
    severity: "warning",
  },
  pct_stroke_ever: {
    label: "Derrame cerebral",
    shortLabel: "Derrame",
    caption: "Adultos que han tenido un derrame cerebral",
    severity: "warning",
  },
  pct_kidney_disease: {
    label: "Enfermedad renal",
    shortLabel: "Renal",
    caption: "Adultos con enfermedad renal",
    severity: "warning",
  },
  pct_current_smoker: {
    label: "Fumadores actuales",
    shortLabel: "Fuma",
    caption: "Adultos que fuman actualmente",
    severity: "neutral",
  },
  pct_binge_drinking: {
    label: "Consumo excesivo de alcohol",
    shortLabel: "Alcohol",
    caption: "Adultos con patrón de consumo excesivo (binge)",
    severity: "neutral",
  },
  pct_fair_or_poor_health: {
    label: "Salud regular o pobre",
    shortLabel: "Salud",
    caption: "Adultos que reportan su salud como regular",
    severity: "neutral",
  },
  pct_no_health_coverage: {
    label: "Sin cobertura de salud",
    shortLabel: "Sin seguro",
    caption: "Adultos sin ningún tipo de cobertura de salud (BRFSS)",
    severity: "neutral",
  },
  pct_heart_attack_ever: {
    label: "Ataque al corazón",
    shortLabel: "IAM",
    caption: "Adultos que han tenido un ataque al corazón",
    severity: "warning",
  },
};

function Sparkline({ values }: { values: TerritoryValue[] }) {
  const numeric = values
    .filter((v) => v.value !== null)
    .map((v) => ({ year: v.year, value: v.value as number }));

  if (numeric.length < 2) {
    return (
      <div className="font-mono text-[9px] uppercase tracking-[0.15em] text-[var(--color-text-subtle)]">
        datos insuficientes
      </div>
    );
  }

  const width = 120;
  const height = 28;
  const padding = 2;
  const xs = numeric.map((_, i) =>
    padding + (i * (width - padding * 2)) / (numeric.length - 1),
  );
  const minV = Math.min(...numeric.map((n) => n.value));
  const maxV = Math.max(...numeric.map((n) => n.value));
  const range = Math.max(maxV - minV, 0.1);
  const ys = numeric.map(
    (n) => height - padding - ((n.value - minV) / range) * (height - padding * 2),
  );
  const pointsAttr = xs.map((x, i) => `${x},${ys[i]}`).join(" ");

  const latestX = xs[xs.length - 1];
  const latestY = ys[ys.length - 1];

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="block"
      aria-hidden="true"
    >
      <polyline
        points={pointsAttr}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={latestX} cy={latestY} r="2.2" fill="currentColor" />
    </svg>
  );
}

function IndicatorCard({
  indicator,
  trend,
}: {
  indicator: TerritoryIndicatorRow;
  trend: TerritoryTrend | null;
}) {
  const meta = DISPLAY[indicator.code] ?? {
    label: indicator.code,
    shortLabel: indicator.code,
    caption: "",
    severity: "neutral" as const,
  };

  const toneClass =
    meta.severity === "alert"
      ? "text-[var(--color-amber)]"
      : meta.severity === "warning"
      ? "text-[var(--color-amber-soft)]"
      : "text-[var(--color-teal-soft)]";

  const value = indicator.latest_value;

  return (
    <div className="flex min-w-[170px] flex-col gap-2 border border-[var(--color-border)] bg-[var(--color-surface)]/40 p-4">
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-[var(--color-text-subtle)]">
          {meta.shortLabel}
        </span>
        <span className="font-mono text-[9px] text-[var(--color-text-subtle)]">
          {indicator.latest_year}
        </span>
      </div>

      <div className={`font-display text-3xl leading-none ${toneClass}`}>
        {value !== null ? `${value.toFixed(1)}%` : "—"}
      </div>

      <div className="text-[11px] leading-snug text-[var(--color-text-muted)]">
        {meta.label}
      </div>

      {trend && (
        <div className={`${toneClass} mt-1`}>
          <Sparkline values={trend.values} />
        </div>
      )}
    </div>
  );
}

export function TerritoryContextPanel() {
  const [indicators, setIndicators] = useState<TerritoryIndicatorRow[] | null>(
    null,
  );
  const [trends, setTrends] = useState<Record<string, TerritoryTrend>>({});
  const [error, setError] = useState<string | null>(null);

  // Load indicator list
  useEffect(() => {
    let cancelled = false;
    fetch("/api/territory/indicators")
      .then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json() as Promise<TerritoryIndicatorRow[]>;
      })
      .then((data) => {
        if (cancelled) return;
        setIndicators(data);
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load trends for each indicator in parallel (cheap, 14-year arrays)
  useEffect(() => {
    if (!indicators) return;
    let cancelled = false;
    Promise.all(
      indicators.map((ind) =>
        fetch(`/api/territory/trend/${ind.code}`)
          .then((r) => (r.ok ? (r.json() as Promise<TerritoryTrend>) : null))
          .catch(() => null),
      ),
    ).then((results) => {
      if (cancelled) return;
      const map: Record<string, TerritoryTrend> = {};
      results.forEach((t) => {
        if (t) map[t.indicator_code] = t;
      });
      setTrends(map);
    });
    return () => {
      cancelled = true;
    };
  }, [indicators]);

  // Hide the whole section if there's nothing to show
  if (error || (indicators !== null && indicators.length === 0)) {
    return null;
  }

  return (
    <section className="mx-auto max-w-7xl px-6 pb-8">
      <div className="mb-5 flex items-end justify-between">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-[var(--color-teal-soft)]">
            Contexto · Puerto Rico en conjunto
          </div>
          <h2 className="mt-2 font-display text-3xl tracking-tight md:text-4xl">
            Enfermedades crónicas
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-[var(--color-text-muted)]">
            Estos indicadores se publican solo a nivel territorial — no existen
            estimados públicos por municipio. Fuente: CDC BRFSS, encuesta anual
            con puertorriqueños adultos.
          </p>
        </div>
      </div>

      {indicators === null ? (
        <div className="font-mono text-xs uppercase tracking-widest text-[var(--color-teal-soft)]">
          Cargando indicadores…
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
          {indicators.map((ind) => (
            <IndicatorCard
              key={ind.code}
              indicator={ind}
              trend={trends[ind.code] ?? null}
            />
          ))}
        </div>
      )}
    </section>
  );
}
