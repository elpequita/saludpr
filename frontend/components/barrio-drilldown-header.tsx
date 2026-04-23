"use client";

import { slugifyMuni } from "@/lib/muni-slugs";

type Props = {
  muniName: string;
  barrioCount: number | null;
};

export function BarrioDrilldownHeader({ muniName, barrioCount }: Props) {
  const handleBack = () => {
    window.dispatchEvent(new CustomEvent("saludpr:zoom-out"));
  };

  const detailHref = `/municipio/${slugifyMuni(muniName)}`;

  return (
    <div className="flex flex-col gap-3 border-t border-[var(--color-border)] bg-[var(--color-surface)]/40 px-5 py-3 backdrop-blur-sm md:flex-row md:items-center md:justify-between">
      <div className="flex flex-wrap items-center gap-3 md:gap-4">
        <button
          onClick={handleBack}
          className="group flex items-center gap-2 border border-[var(--color-border)] bg-[var(--color-ink)] px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.15em] text-[var(--color-text-muted)] transition-colors hover:border-[var(--color-amber)] hover:text-[var(--color-text)]"
          aria-label="Volver al mapa completo"
        >
          <span className="transition-transform group-hover:-translate-x-0.5">←</span>
          <span>Volver a la isla</span>
        </button>

        <div className="flex items-baseline gap-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-subtle)]">
            Viendo barrios de
          </span>
          <span className="font-display text-lg text-[var(--color-amber)]">
            {muniName}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {barrioCount !== null && (
          <div className="hidden font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-subtle)] md:block">
            {barrioCount} barrio{barrioCount === 1 ? "" : "s"} · escala
            recalculada
          </div>
        )}
        <a
          href={detailHref}
          className="group flex items-center gap-2 border border-[var(--color-amber)]/60 bg-[var(--color-amber)]/10 px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.15em] text-[var(--color-amber)] transition-colors hover:border-[var(--color-amber)] hover:bg-[var(--color-amber)]/20"
        >
          <span>Ver detalle de {muniName}</span>
          <span className="transition-transform group-hover:translate-x-0.5">
            →
          </span>
        </a>
      </div>
    </div>
  );
}
