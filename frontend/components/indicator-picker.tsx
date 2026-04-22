"use client";

import { useMemo } from "react";
import {
  INDICATORS,
  COLOR_RAMPS,
  formatValue,
  type IndicatorMeta,
} from "@/lib/indicators";

type Props = {
  indicator: string;
  year: number;
  availableIndicators: string[];
  availableYears: number[];
  breaks: number[] | null;
  onIndicatorChange: (code: string) => void;
  onYearChange: (year: number) => void;
};

export function IndicatorPicker({
  indicator,
  year,
  availableIndicators,
  availableYears,
  breaks,
  onIndicatorChange,
  onYearChange,
}: Props) {
  const meta: IndicatorMeta | undefined = INDICATORS[indicator];
  const ramp = COLOR_RAMPS[meta?.direction ?? "neutral"];

  const ordered = useMemo(() => {
    return [...availableIndicators].sort((a, b) => {
      const aMeta = INDICATORS[a];
      const bMeta = INDICATORS[b];
      if (!aMeta) return 1;
      if (!bMeta) return -1;
      return aMeta.short_es.localeCompare(bMeta.short_es);
    });
  }, [availableIndicators]);

  return (
    <div className="flex flex-col gap-5 border border-[var(--color-border)] bg-[var(--color-surface)]/60 p-5 backdrop-blur-sm md:flex-row md:items-start md:justify-between">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:gap-6">
        <label className="flex flex-col gap-1.5">
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-subtle)]">
            Indicador
          </span>
          <select
            value={indicator}
            onChange={(e) => onIndicatorChange(e.target.value)}
            className="w-full min-w-[220px] cursor-pointer border border-[var(--color-border)] bg-[var(--color-ink)] px-3 py-2 text-sm text-[var(--color-text)] outline-none transition-colors focus:border-[var(--color-amber)] md:w-auto"
          >
            {ordered.map((code) => {
              const m = INDICATORS[code];
              return (
                <option key={code} value={code}>
                  {m ? m.label_es : code}
                </option>
              );
            })}
          </select>
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-subtle)]">
            Año
          </span>
          <select
            value={year}
            onChange={(e) => onYearChange(Number(e.target.value))}
            className="cursor-pointer border border-[var(--color-border)] bg-[var(--color-ink)] px-3 py-2 text-sm text-[var(--color-text)] outline-none transition-colors focus:border-[var(--color-amber)]"
          >
            {availableYears.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>

        {meta?.description_es && (
          <p className="max-w-xs text-xs italic text-[var(--color-text-muted)]">
            {meta.description_es}
          </p>
        )}
      </div>

      {/* Legend */}
      {breaks && meta && (
        <div className="flex flex-col gap-1.5 md:items-end">
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-subtle)]">
            {meta.short_es}
          </div>
          <div className="flex items-center gap-1">
            {ramp.map((color, i) => (
              <div
                key={color}
                className="flex flex-col items-center gap-1"
                style={{ width: "52px" }}
              >
                <div
                  className="h-4 w-full"
                  style={{ backgroundColor: color }}
                />
                <div className="text-[10px] text-[var(--color-text-muted)]">
                  {i === 0 || i === ramp.length - 1
                    ? formatValue(breaks[i === 0 ? 0 : 5] ?? null, meta.unit)
                    : ""}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
