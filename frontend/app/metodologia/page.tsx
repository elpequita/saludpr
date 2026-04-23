"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";

type DataSource = {
  slug: string;
  name: string;
  organization: string;
  url: string;
  license: string;
  update_frequency: string | null;
  description_es: string | null;
  known_limitations: string | null;
  last_pulled_at: string | null;
  latest_data_year: number | null;
  latest_successful_run: string | null;
  muni_metric_rows: number;
  barrio_metric_rows: number;
};

function formatRelativeTime(iso: string | null): string {
  if (!iso) return "nunca";
  const then = new Date(iso).getTime();
  const diffMs = Date.now() - then;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "hoy";
  if (diffDays === 1) return "hace 1 día";
  if (diffDays < 30) return `hace ${diffDays} días`;
  const months = Math.floor(diffDays / 30);
  if (months === 1) return "hace 1 mes";
  if (months < 12) return `hace ${months} meses`;
  const years = Math.floor(months / 12);
  return years === 1 ? "hace 1 año" : `hace ${years} años`;
}

export default function MetodologiaPage() {
  const [sources, setSources] = useState<DataSource[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/data-sources")
      .then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json() as Promise<DataSource[]>;
      })
      .then((data) => {
        if (!cancelled) setSources(data);
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load sources");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const activeSources = sources?.filter((s) => s.last_pulled_at !== null) ?? [];
  const pendingSources = sources?.filter((s) => s.last_pulled_at === null) ?? [];

  return (
    <main className="relative z-10 min-h-screen">
      <SiteHeader />

      {/* Hero */}
      <section className="mx-auto max-w-4xl px-6 pt-16 md:pt-24">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-[var(--color-teal-soft)] rise rise-1">
          Metodología · Auditoría pública
        </p>
        <h1 className="mt-5 font-display text-5xl leading-[1.05] tracking-tight text-[var(--color-text)] md:text-6xl rise rise-2">
          Cada número,{" "}
          <span className="italic text-[var(--color-amber-soft)]">
            rastreable
          </span>
          .
        </h1>
        <p className="mt-6 text-lg leading-relaxed text-[var(--color-text-muted)] rise rise-3">
          Esta página muestra de dónde viene cada dato en SaludPR, cuándo lo
          procesamos por última vez, y qué limitaciones conoces para interpretarlo
          correctamente. Se actualiza automáticamente cada vez que corremos una
          pipeline de ingestión.
        </p>
      </section>

      {/* Content */}
      <article className="mx-auto max-w-3xl px-6 py-16">
        <div className="rise rise-4 space-y-14">
          {/* Sources section */}
          <section>
            <div className="flex items-center gap-3">
              <div className="h-px w-8 bg-[var(--color-amber)]" />
              <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[var(--color-text-subtle)]">
                01 · Fuentes de datos
              </span>
            </div>
            <h2 className="mt-4 font-display text-3xl tracking-tight text-[var(--color-text)]">
              De dónde viene la data.
            </h2>
            <p className="mt-3 text-[15px] leading-relaxed text-[var(--color-text-muted)]">
              Todas las fuentes son públicas, consultables gratuitamente, y sus
              datos se publican bajo licencias abiertas. No compramos ni
              accedemos a ningún dataset privado.
            </p>

            {error && (
              <div className="mt-6 border border-[var(--color-rose)]/40 bg-[var(--color-rose)]/10 p-4 text-sm text-[var(--color-rose)]">
                No pude cargar la lista de fuentes desde la API: {error}.
              </div>
            )}

            {sources === null && !error && (
              <div className="mt-6 font-mono text-xs uppercase tracking-widest text-[var(--color-teal-soft)]">
                Cargando fuentes…
              </div>
            )}

            {activeSources.length > 0 && (
              <div className="mt-6 space-y-4">
                <h3 className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-tealSoft,var(--color-teal-soft))]">
                  Activas · con datos cargados
                </h3>
                {activeSources.map((src) => (
                  <SourceCard key={src.slug} source={src} />
                ))}
              </div>
            )}

            {pendingSources.length > 0 && (
              <div className="mt-8 space-y-4">
                <h3 className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-subtle)]">
                  Planificadas · aún no cargadas
                </h3>
                {pendingSources.map((src) => (
                  <SourceCard key={src.slug} source={src} pending />
                ))}
              </div>
            )}
          </section>

          {/* Processing section */}
          <section>
            <div className="flex items-center gap-3">
              <div className="h-px w-8 bg-[var(--color-amber)]" />
              <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[var(--color-text-subtle)]">
                02 · Procesamiento
              </span>
            </div>
            <h2 className="mt-4 font-display text-3xl tracking-tight text-[var(--color-text)]">
              Cómo procesamos la data.
            </h2>
            <div className="mt-6 space-y-5 text-[15px] leading-relaxed text-[var(--color-text-muted)]">
              <p>
                Toda la ingestión ocurre en módulos de Python que descargan
                directamente de las APIs y archivos oficiales de cada fuente.
                Cada corrida registra en la base de datos: qué fuente, qué
                timestamp, cuántas filas leídas, cuántas insertadas, cuántas
                omitidas, y el resultado final.
              </p>
              <p>
                Los datos calculados (por ejemplo, porcentajes derivados de
                conteos) se computan de forma explícita con numerador y
                denominador almacenados — no inventamos inferencias. Cualquier
                persona puede replicar los cálculos directamente desde las
                variables Census crudas.
              </p>
              <p>
                Usamos{" "}
                <code className="bg-[var(--color-surface)] px-1.5 py-0.5 text-[13px] text-[var(--color-amber)]">
                  UPSERT
                </code>{" "}
                idempotente — correr el mismo pipeline dos veces produce el
                mismo resultado. Si una API falla parcialmente, la corrida se
                marca como fallida y se revierten los cambios.
              </p>
            </div>
          </section>

          {/* Reliability */}
          <section>
            <div className="flex items-center gap-3">
              <div className="h-px w-8 bg-[var(--color-amber)]" />
              <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[var(--color-text-subtle)]">
                03 · Supresión y confiabilidad
              </span>
            </div>
            <h2 className="mt-4 font-display text-3xl tracking-tight text-[var(--color-text)]">
              Cuándo un número es demasiado pequeño.
            </h2>
            <div className="mt-6 space-y-5 text-[15px] leading-relaxed text-[var(--color-text-muted)]">
              <p>
                Algunos barrios de Puerto Rico tienen muestras muy pequeñas en
                las encuestas federales — poblaciones de menos de 100 personas
                son comunes. Cuando calculas un porcentaje sobre una muestra de
                esos tamaños, el resultado tiene un margen de error enorme.
              </p>
              <p>
                Por eso aplicamos dos reglas:
              </p>
              <ul className="ml-0 list-none space-y-3">
                <li className="flex gap-3 border-l-2 border-[var(--color-amber)] pl-4">
                  <div>
                    <span className="font-display text-[var(--color-text)]">
                      Supresión nativa.
                    </span>{" "}
                    Cuando Census marca un valor como suprimido (códigos
                    sentinela negativos), lo almacenamos como{" "}
                    <code className="text-[13px] text-[var(--color-amber)]">
                      NULL
                    </code>{" "}
                    con la bandera{" "}
                    <code className="text-[13px] text-[var(--color-amber)]">
                      is_suppressed = true
                    </code>{" "}
                    y no lo mostramos en el mapa.
                  </div>
                </li>
                <li className="flex gap-3 border-l-2 border-[var(--color-amber)] pl-4">
                  <div>
                    <span className="font-display text-[var(--color-text)]">
                      Umbral de confiabilidad.
                    </span>{" "}
                    En la vista de barrios, los que tienen población menor a
                    1,000 residentes se renderizan atenuados (35% de opacidad).
                    Sus valores siguen disponibles vía API, pero visualmente se
                    señalan como "alta variabilidad" para no engañar al ojo con
                    porcentajes extremos basados en 7 o 30 personas.
                  </div>
                </li>
              </ul>
            </div>
          </section>

          {/* Limitations */}
          <section>
            <div className="flex items-center gap-3">
              <div className="h-px w-8 bg-[var(--color-amber)]" />
              <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[var(--color-text-subtle)]">
                04 · Limitaciones conocidas
              </span>
            </div>
            <h2 className="mt-4 font-display text-3xl tracking-tight text-[var(--color-text)]">
              Lo que SaludPR todavía no puede hacer.
            </h2>
            <div className="mt-6 space-y-5 text-[15px] leading-relaxed text-[var(--color-text-muted)]">
              <p>
                <span className="text-[var(--color-text)]">
                  CDC PLACES excluye a Puerto Rico.
                </span>{" "}
                El estándar federal para tasas de enfermedades crónicas (diabetes,
                hipertensión, obesidad) a nivel sub-estatal no incluye a los
                territorios. Esto significa que SaludPR todavía no tiene tasas
                directas de enfermedades crónicas a nivel municipio. Estamos
                evaluando alternativas: usar BRFSS a nivel territorio, integrar
                data de PR DoH, o colaborar con agencias federales.
              </p>
              <p>
                <span className="text-[var(--color-text)]">
                  Márgenes de error ACS.
                </span>{" "}
                Los datos de ACS/PRCS vienen con intervalos de confianza que
                actualmente no mostramos. Para indicadores municipales son
                pequeños; para barrios, pueden ser significativos. Versión
                futura incluirá estos intervalos en los tooltips.
              </p>
              <p>
                <span className="text-[var(--color-text)]">
                  No todos los barrios tienen población registrada.
                </span>{" "}
                Algunos barrios muy rurales aparecen sin valor en la columna{" "}
                <code className="text-[13px] text-[var(--color-amber)]">
                  population_latest
                </code>
                , lo que dificulta aplicar el umbral de confiabilidad
                automáticamente. Esos se asumen "reliable" por default, lo cual
                puede ser incorrecto. Investigación en progreso.
              </p>
            </div>
          </section>

          {/* How to verify */}
          <section>
            <div className="flex items-center gap-3">
              <div className="h-px w-8 bg-[var(--color-amber)]" />
              <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[var(--color-text-subtle)]">
                05 · Cómo verificar
              </span>
            </div>
            <h2 className="mt-4 font-display text-3xl tracking-tight text-[var(--color-text)]">
              Cómo auditar cualquier número.
            </h2>
            <div className="mt-6 space-y-5 text-[15px] leading-relaxed text-[var(--color-text-muted)]">
              <p>
                Cualquier persona — periodista, investigadora, auditor — puede
                verificar independientemente cualquier número mostrado en
                SaludPR siguiendo estos pasos:
              </p>
              <ol className="ml-4 list-decimal space-y-2">
                <li>
                  Identifica el indicador (ej.{" "}
                  <code className="text-[13px] text-[var(--color-amber)]">
                    pct_below_poverty
                  </code>
                  ), el municipio o barrio, y el año.
                </li>
                <li>
                  Consulta nuestra API pública:{" "}
                  <code className="text-[13px] text-[var(--color-amber)]">
                    GET /api/metrics/pct_below_poverty?year=2023
                  </code>
                </li>
                <li>
                  La respuesta incluye el valor, el numerador, el denominador y
                  el ID de la fuente.
                </li>
                <li>
                  Cruza ese dato contra la fuente original (ej.{" "}
                  <a
                    href="https://data.census.gov"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[var(--color-amber)] underline-offset-4 hover:underline"
                  >
                    data.census.gov
                  </a>
                  ) usando los códigos de variable ACS documentados en el
                  repositorio.
                </li>
              </ol>
              <p>
                Si encuentras una discrepancia, reportala como bug en{" "}
                <a
                  href="https://github.com/elpequita/saludpr/issues"
                  target="_blank"
                  rel="noreferrer"
                  className="text-[var(--color-amber)] underline-offset-4 hover:underline"
                >
                  GitHub Issues
                </a>
                . Tomamos los reportes en serio.
              </p>
            </div>
          </section>

          {/* Footer nav */}
          <div className="flex justify-between border-t border-[var(--color-border)] pt-6">
            <Link
              href="/acerca"
              className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            >
              ← Acerca del proyecto
            </Link>
            <Link
              href="/"
              className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--color-amber)] hover:text-[var(--color-amber-soft)]"
            >
              Ir al mapa →
            </Link>
          </div>
        </div>
      </article>

      <SiteFooter />
    </main>
  );
}

// --- Source card component ---
function SourceCard({
  source,
  pending = false,
}: {
  source: DataSource;
  pending?: boolean;
}) {
  return (
    <div
      className={`border ${
        pending
          ? "border-[var(--color-border)] bg-[var(--color-surface)]/20"
          : "border-[var(--color-border)] bg-[var(--color-surface)]/50"
      } p-5`}
    >
      {/* Header: name + status */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-display text-lg text-[var(--color-text)]">
            {source.name}
          </h4>
          <p className="mt-0.5 text-[12px] text-[var(--color-text-subtle)]">
            {source.organization} · {source.license}
          </p>
        </div>
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-amber)] underline-offset-4 hover:underline"
        >
          Fuente ↗
        </a>
      </div>

      {/* Description */}
      {source.description_es && (
        <p className="mt-3 text-[14px] leading-relaxed text-[var(--color-text-muted)]">
          {source.description_es}
        </p>
      )}

      {/* Stats strip — only for active sources */}
      {!pending && (
        <div className="mt-4 grid grid-cols-2 gap-3 border-t border-[var(--color-border)] pt-3 md:grid-cols-4">
          <Stat
            label="Última carga"
            value={formatRelativeTime(source.latest_successful_run)}
          />
          <Stat
            label="Año más reciente"
            value={source.latest_data_year?.toString() ?? "—"}
          />
          <Stat
            label="Filas muni"
            value={source.muni_metric_rows.toLocaleString("es-PR")}
          />
          <Stat
            label="Filas barrio"
            value={source.barrio_metric_rows.toLocaleString("es-PR")}
          />
        </div>
      )}

      {/* Known limitations */}
      {source.known_limitations && (
        <div className="mt-4 border-l-2 border-[var(--color-amber)] pl-3 text-[12px] leading-relaxed text-[var(--color-text-muted)]">
          <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-[var(--color-amber-soft)]">
            Limitaciones conocidas
          </span>
          <p className="mt-1">{source.known_limitations}</p>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-[var(--color-text-subtle)]">
        {label}
      </div>
      <div className="mt-0.5 font-display text-[13px] text-[var(--color-text)]">
        {value}
      </div>
    </div>
  );
}
