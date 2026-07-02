import type { MetadataRoute } from "next";

const SITE_URL = "https://saludpr.dataurea.com";

type SlugMapping = { id: string; slug: string; name: string };

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE_URL}/acerca`, changeFrequency: "monthly", priority: 0.7 },
    {
      url: `${SITE_URL}/metodologia`,
      changeFrequency: "monthly",
      priority: 0.7,
    },
  ];

  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.API_BASE_URL ||
    "http://127.0.0.1:8000";

  // Municipality pages come from the API; if it is unreachable the sitemap
  // still serves the static routes rather than failing the request.
  let muniRoutes: MetadataRoute.Sitemap = [];
  try {
    const res = await fetch(`${baseUrl}/api/municipalities-slugs`, {
      next: { revalidate: 86400 },
    });
    if (res.ok) {
      const mappings = (await res.json()) as SlugMapping[];
      muniRoutes = mappings.map((m) => ({
        url: `${SITE_URL}/municipio/${m.slug}`,
        changeFrequency: "weekly" as const,
        priority: 0.8,
      }));
    }
  } catch {
    // API down — serve static routes only.
  }

  return [...staticRoutes, ...muniRoutes];
}
