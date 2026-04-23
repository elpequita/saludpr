"use client";

import { INDICATORS, formatValue } from "@/lib/indicators";
import { slugifyMuni } from "@/lib/muni-slugs";

// ---------- Barrio ranking ----------

type BarrioRankEntry = {
  id: string;
  name: string;
  value: number | null;
  population_latest: number | null;
};

type BarrioRanking = {
  indicator_code: string;
  direction: string; // 'worst_first' or 'best_first'
  year: number | null;
  top: BarrioRankEntry[];
  bottom: BarrioRankEntry[];
};

export function BarrioRankingPanel({
  ranking,
  muniName,
}: {
  ranking: BarrioRanking;
  muniName: string;
}) {
  const meta = INDICATORS[ranking.indicator_code];
  const label = meta?.label_es ?? ranking.indicator_code;
  const unit = meta?.unit ?? "count";

  const worstLabel =
    ranking.direction === "worst_first" ? "Mayor " : "Mayor ";
  const bestLabel =
    ranking.direction === "worst_first" ? "Menor " : "Menor ";

  return (
    <section id="barrios" className="mx-auto max-w-5xl px-6 py-16">
      <div className="mb-6">
        <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-[var(--color-teal-soft)]">
          Barrios de {muniName}
        </div>
        <h2 className="mt-2 font-display text-3xl tracking-tight md:text-4xl">
          Dentro del municipio
        </h2>
        <p className="mt-2 text-sm text-[var(--color-text-muted)]">
          Top y fondo por {label.toLowerCase()} · barrios con &gt;1,000
          habitantes · {ranking.year && <>año {ranking.year}</>}
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Highest */}
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)]/40 p-5">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-amber)]">
            {worstLabel}
            {label.toLowerCase()}
          </h3>
          <ul className="mt-3 divide-y divide-[var(--color-border)]">
            {ranking.top.map((b, i) => (
              <li
                key={b.id}
                className="flex items-baseline justify-between gap-3 py-2"
              >
                <span className="flex items-baseline gap-3">
                  <span className="font-mono text-xs text-[var(--color-text-subtle)]">
                    #{i + 1}
                  </span>
                  <span className="font-display text-base text-[var(--color-text)]">
                    {b.name}
                  </span>
                  {b.population_latest !== null && (
                    <span className="font-mono text-[10px] text-[var(--color-text-subtle)]">
                      {b.population_latest.toLocaleString("es-PR")} hab.
                    </span>
                  )}
                </span>
                <span className="font-display text-lg text-[var(--color-amber)]">
                  {b.value !== null ? formatValue(b.value, unit) : "—"}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Lowest */}
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)]/40 p-5">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-teal-soft)]">
            {bestLabel}
            {label.toLowerCase()}
          </h3>
          <ul className="mt-3 divide-y divide-[var(--color-border)]">
            {ranking.bottom.map((b, i) => (
              <li
                key={b.id}
                className="flex items-baseline justify-between gap-3 py-2"
              >
                <span className="flex items-baseline gap-3">
                  <span className="font-mono text-xs text-[var(--color-text-subtle)]">
                    #{i + 1}
                  </span>
                  <span className="font-display text-base text-[var(--color-text)]">
                    {b.name}
                  </span>
                  {b.population_latest !== null && (
                    <span className="font-mono text-[10px] text-[var(--color-text-subtle)]">
                      {b.population_latest.toLocaleString("es-PR")} hab.
                    </span>
                  )}
                </span>
                <span className="font-display text-lg text-[var(--color-teal-soft)]">
                  {b.value !== null ? formatValue(b.value, unit) : "—"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

// ---------- Similar munis ----------

type SimilarMuni = {
  id: string;
  name: string;
  population_latest: number | null;
  population_diff_pct: number;
};

export function SimilarMunisPanel({
  similar,
  currentName,
}: {
  similar: SimilarMuni[];
  currentName: string;
}) {
  if (similar.length === 0) return null;

  return (
    <section id="similares" className="mx-auto max-w-5xl px-6 py-16">
      <div className="mb-6">
        <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-[var(--color-teal-soft)]">
          Municipios similares
        </div>
        <h2 className="mt-2 font-display text-3xl tracking-tight md:text-4xl">
          Comparar con vecinos demográficos
        </h2>
        <p className="mt-2 text-sm text-[var(--color-text-muted)]">
          Los 4 municipios con población más parecida a {currentName}.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {similar.map((m) => (
          <a
            key={m.id}
            href={`/municipio/${slugifyMuni(m.name)}`}
            className="group flex flex-col gap-2 border border-[var(--color-border)] bg-[var(--color-surface)]/40 p-4 transition-colors hover:border-[var(--color-amber)]"
          >
            <div className="font-display text-xl text-[var(--color-text)] transition-colors group-hover:text-[var(--color-amber)]">
              {m.name}
            </div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-subtle)]">
              {m.population_latest !== null && (
                <>
                  {m.population_latest.toLocaleString("es-PR")} hab. ·{" "}
                </>
              )}
              ±{m.population_diff_pct.toFixed(0)}%
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}
