import { headers } from "next/headers";

type Health = {
  status: string;
  database: string;
  municipalities_loaded: number;
};

async function getHealth(): Promise<Health | null> {
  try {
    // Use a relative URL in browser / server-side use absolute
    const base =
      process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api";
    const res = await fetch(`${base}/health`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return (await res.json()) as Health;
  } catch {
    return null;
  }
}

export async function StatsBar() {
  // Next 15 uses async headers() — just to trigger dynamic render for freshness
  await headers();
  const health = await getHealth();

  const stats = [
    {
      value: health?.municipalities_loaded ?? 78,
      label: "Municipios",
      sub: "mapeados",
    },
    {
      value: 8,
      label: "Fuentes",
      sub: "públicas",
    },
    {
      value: 0,
      label: "Indicadores",
      sub: "disponibles · pronto",
    },
    {
      value: health?.status === "ok" ? "LIVE" : "OFFLINE",
      label: "API",
      sub: health?.database === "ok" ? "conectada" : "sin conexión",
      isString: true,
    },
  ];

  return (
    <section className="border-y border-[var(--color-border)] bg-[var(--color-surface)]/40 backdrop-blur-sm rise rise-4">
      <div className="mx-auto grid max-w-7xl grid-cols-2 divide-x divide-[var(--color-border)] md:grid-cols-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="flex items-baseline justify-between gap-4 px-6 py-5"
          >
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-[var(--color-text-subtle)]">
                {stat.label}
              </div>
              <div className="mt-1 text-xs text-[var(--color-text-muted)]">
                {stat.sub}
              </div>
            </div>
            <div
              className={`font-display ${
                stat.isString ? "text-2xl" : "text-4xl"
              } leading-none ${
                stat.value === "LIVE"
                  ? "text-[var(--color-teal-soft)]"
                  : stat.value === "OFFLINE"
                  ? "text-[var(--color-rose)]"
                  : "text-[var(--color-text)]"
              }`}
            >
              {stat.value}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
