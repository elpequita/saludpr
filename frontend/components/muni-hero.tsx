"use client";

type Designation = {
  designation_code: string;
  designation_name: string;
  imu_score: number | null;
  designation_year: number | null;
  rural_status: string | null;
};

type Props = {
  id: string;
  name: string;
  population_latest: number | null;
  area_sq_km: number | null;
  designation: Designation | null;
};

export function MuniHero({
  id,
  name,
  population_latest,
  area_sq_km,
  designation,
}: Props) {
  return (
    <section className="mx-auto max-w-5xl px-6 pt-12 md:pt-16">
      {/* Back link */}
      <a
        href="/"
        className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text)] rise rise-1"
      >
        <span>←</span>
        <span>Volver al mapa</span>
      </a>

      {/* Muni name */}
      <h1 className="mt-5 font-display text-5xl leading-[1.0] tracking-tight text-[var(--color-text)] md:text-7xl rise rise-2">
        {name}
      </h1>

      {/* Subtitle — designation status if applicable */}
      {designation && (
        <p className="mt-3 font-display text-lg italic text-[var(--color-amber-soft)] md:text-xl rise rise-3">
          🏥 Medically Underserved
          {designation.designation_year && (
            <> desde {designation.designation_year}</>
          )}
          {designation.imu_score !== null && (
            <span className="text-[var(--color-text-muted)] not-italic">
              {" "}
              · IMU {designation.imu_score.toFixed(2)} /100
            </span>
          )}
        </p>
      )}

      {/* Quick stats strip */}
      <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm text-[var(--color-text-muted)] rise rise-4">
        {population_latest !== null && (
          <span>
            <span className="font-display text-[var(--color-text)]">
              {population_latest.toLocaleString("es-PR")}
            </span>{" "}
            habitantes
          </span>
        )}
        {area_sq_km !== null && (
          <span>
            <span className="font-display text-[var(--color-text)]">
              {area_sq_km.toFixed(1)}
            </span>{" "}
            km²
          </span>
        )}
        <span>
          <span className="font-mono text-xs uppercase tracking-widest text-[var(--color-text-subtle)]">
            FIPS
          </span>{" "}
          <span className="font-mono text-[var(--color-text)]">{id}</span>
        </span>
        {designation?.rural_status && (
          <span>
            <span className="font-mono text-xs uppercase tracking-widest text-[var(--color-text-subtle)]">
              Ruralidad
            </span>{" "}
            <span className="text-[var(--color-text)]">
              {designation.rural_status}
            </span>
          </span>
        )}
      </div>
    </section>
  );
}
