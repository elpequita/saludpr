import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { MuniHero } from "@/components/muni-hero";
import { MuniSdohGrid } from "@/components/muni-sdoh-grid";
import {
  BarrioRankingPanel,
  SimilarMunisPanel,
} from "@/components/muni-secondary-panels";

type MuniDetailApi = {
  id: string;
  name: string;
  area_sq_km: number | null;
  population_latest: number | null;
  designation: {
    designation_code: string;
    designation_name: string;
    imu_score: number | null;
    designation_year: number | null;
    rural_status: string | null;
  } | null;
  indicators: {
    code: string;
    value_type: string | null;
    values: { year: number; value: number | null }[];
    latest_year: number | null;
    latest_value: number | null;
    source_slug: string | null;
  }[];
  barrio_ranking: {
    indicator_code: string;
    direction: string;
    year: number | null;
    top: {
      id: string;
      name: string;
      value: number | null;
      population_latest: number | null;
    }[];
    bottom: {
      id: string;
      name: string;
      value: number | null;
      population_latest: number | null;
    }[];
  } | null;
  similar_munis: {
    id: string;
    name: string;
    population_latest: number | null;
    population_diff_pct: number;
  }[];
};

type SlugMapping = { id: string; slug: string; name: string };

/**
 * Server-side resolver. Accepts either FIPS or slug, returns the MuniDetail
 * payload or null if not found.
 */
async function loadMuniDetail(param: string): Promise<MuniDetailApi | null> {
  // Determine the base URL for the API. In dev, the backend is at localhost:8000,
  // but Next.js rewrites proxy /api/* to it. For SSR we need an absolute URL.
  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.API_BASE_URL ||
    "http://127.0.0.1:8000";

  // 1. Resolve the slug if needed
  let fips: string;
  if (/^\d{5}$/.test(param)) {
    fips = param;
  } else {
    const slugRes = await fetch(`${baseUrl}/api/municipalities-slugs`, {
      cache: "no-store",
    });
    if (!slugRes.ok) return null;
    const mappings = (await slugRes.json()) as SlugMapping[];
    const match = mappings.find((m) => m.slug === param.toLowerCase());
    if (!match) return null;
    fips = match.id;
  }

  // 2. Fetch the detail payload
  const r = await fetch(`${baseUrl}/api/municipalities/${fips}/detail`, {
    cache: "no-store",
  });
  if (!r.ok) return null;
  return (await r.json()) as MuniDetailApi;
}

// ---------- Metadata ----------

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const detail = await loadMuniDetail(slug);
  if (!detail) {
    return { title: "Municipio no encontrado · SaludPR" };
  }

  const pop = detail.population_latest;
  const descParts = [
    `Datos de salud pública para ${detail.name}, Puerto Rico.`,
    pop && `Población ${pop.toLocaleString("es-PR")}.`,
    detail.designation &&
      `Federalmente designado como Medically Underserved desde ${detail.designation.designation_year}.`,
    "Indicadores sociales, chronic conditions, y rankings de barrios. Un proyecto de Dataurea.",
  ].filter(Boolean);

  return {
    title: `${detail.name} · SaludPR`,
    description: descParts.join(" "),
  };
}

// ---------- Page ----------

export default async function MuniDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const detail = await loadMuniDetail(slug);
  if (!detail) notFound();

  return (
    <main className="relative z-10 min-h-screen">
      <SiteHeader />

      <MuniHero
        id={detail.id}
        name={detail.name}
        population_latest={detail.population_latest}
        area_sq_km={detail.area_sq_km}
        designation={detail.designation}
      />

      <MuniSdohGrid indicators={detail.indicators} />

      {detail.barrio_ranking && detail.barrio_ranking.top.length > 0 && (
        <BarrioRankingPanel
          ranking={detail.barrio_ranking}
          muniName={detail.name}
        />
      )}

      <SimilarMunisPanel similar={detail.similar_munis} currentName={detail.name} />

      <SiteFooter />
    </main>
  );
}
