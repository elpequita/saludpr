/**
 * Slugify a PR municipio name. MUST match the server-side _slugify() in
 * backend/app/routers/municipalities.py.
 *
 * Examples:
 *   "San Juan"    -> "san-juan"
 *   "Loíza"       -> "loiza"
 *   "Peñuelas"    -> "penuelas"
 *   "Las Marías"  -> "las-marias"
 */
export function slugifyMuni(name: string): string {
  return name
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "") // strip combining marks
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "") // keep only alnum + space + hyphen
    .trim()
    .split(/\s+/)
    .join("-");
}

/** Reverse: accept either FIPS (5 digits) or slug, return "fips" or "slug". */
export function identifyMuniParam(param: string): "fips" | "slug" {
  return /^\d{5}$/.test(param) ? "fips" : "slug";
}

export type MuniSlugMapping = {
  id: string;
  slug: string;
  name: string;
};

/**
 * Fetch the slug mapping table. Cached for the session in module scope —
 * it's small (78 rows) and stable.
 */
let _cachedMapping: MuniSlugMapping[] | null = null;

export async function loadMuniSlugs(): Promise<MuniSlugMapping[]> {
  if (_cachedMapping) return _cachedMapping;
  const r = await fetch("/api/municipalities-slugs");
  if (!r.ok) throw new Error(`Slug API ${r.status}`);
  const data = (await r.json()) as MuniSlugMapping[];
  _cachedMapping = data;
  return data;
}

/** Resolve a URL param (either FIPS or slug) to { id, slug, name }. */
export async function resolveMuniParam(
  param: string,
): Promise<MuniSlugMapping | null> {
  const mappings = await loadMuniSlugs();
  const paramLower = param.toLowerCase();
  // Try FIPS first (cheap), then slug
  if (/^\d{5}$/.test(param)) {
    return mappings.find((m) => m.id === param) ?? null;
  }
  return mappings.find((m) => m.slug === paramLower) ?? null;
}
