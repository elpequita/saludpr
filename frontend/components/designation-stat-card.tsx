"use client";

import { useEffect, useState } from "react";

type DesignationSummary = {
  total_munis: number;
  designated_munis: number;
  percentage_designated: number;
  min_imu_score: number | null;
  max_imu_score: number | null;
  mean_imu_score: number | null;
  earliest_designation: string | null;
  counts_by_type: Record<string, number>;
  counts_by_rural_status: Record<string, number>;
  source_slug: string;
  last_updated: string | null;
};

export function DesignationStatCard() {
  const [data, setData] = useState<DesignationSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/designations/summary")
      .then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json() as Promise<DesignationSummary>;
      })
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Hide the card silently if data isn't loaded — don't claim if we can't prove
  if (error || !data || data.designated_munis === 0) {
    return null;
  }

  const earliestYear = data.earliest_designation
    ? new Date(data.earliest_designation).getUTCFullYear()
    : null;

  const ruralCount =
    (data.counts_by_rural_status["Rural"] ?? 0) +
    (data.counts_by_rural_status["Partially Rural"] ?? 0);

  return (
    <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-[1.3fr_1fr_1fr]">
      {/* Main headline stat */}
      <div className="relative overflow-hidden border border-[var(--color-border)] bg-[var(--color-surface)]/50 p-6">
        <div className="absolute left-0 top-0 h-full w-1 bg-[var(--color-amber)]" />
        <div className="pl-3">
          <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-[var(--color-teal-soft)]">
            Designación federal · HRSA MUA/P
          </div>
          <div className="mt-3 flex items-baseline gap-3">
            <span className="font-display text-6xl leading-none text-[var(--color-amber)]">
              {data.designated_munis}
            </span>
            <span className="font-display text-3xl text-[var(--color-text-muted)]">
              de {data.total_munis}
            </span>
          </div>
          <p className="mt-3 text-[15px] leading-snug text-[var(--color-text)]">
            municipios están federalmente designados como{" "}
            <span className="text-[var(--color-text)] italic">
              Medically Underserved
            </span>
            .
          </p>
          <p className="mt-1 text-[12px] text-[var(--color-text-muted)]">
            {data.percentage_designated.toFixed(0)}% de la isla — el gobierno
            federal reconoce que no hay suficiente atención primaria para la
            mayoría de los municipios.
          </p>
        </div>
      </div>

      {/* IMU severity */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)]/40 p-5">
        <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-subtle)]">
          Severidad (IMU Score)
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="font-display text-4xl text-[var(--color-amber-soft)]">
            {data.mean_imu_score !== null ? data.mean_imu_score.toFixed(1) : "—"}
          </span>
          <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">
            promedio
          </span>
        </div>
        <p className="mt-2 text-[11px] leading-snug text-[var(--color-text-muted)]">
          Escala 0–100, <span className="text-[var(--color-text)]">menor = peor</span>.
          Rango PR:{" "}
          {data.min_imu_score !== null
            ? `${data.min_imu_score.toFixed(1)} – ${data.max_imu_score?.toFixed(1) ?? "—"}`
            : "—"}
          . Umbral de designación: 62.
        </p>
      </div>

      {/* Timeline + rural */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)]/40 p-5">
        <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-subtle)]">
          Contexto histórico
        </div>
        <div className="mt-3 space-y-2">
          {earliestYear && (
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-display text-2xl text-[var(--color-tealSoft,var(--color-teal-soft))]">
                {earliestYear}
              </span>
              <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">
                primera designación
              </span>
            </div>
          )}
          {ruralCount > 0 && (
            <div className="flex items-baseline justify-between gap-2 border-t border-[var(--color-border)] pt-2">
              <span className="font-display text-2xl text-[var(--color-tealSoft,var(--color-teal-soft))]">
                {ruralCount}
              </span>
              <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">
                rurales o semirurales
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
