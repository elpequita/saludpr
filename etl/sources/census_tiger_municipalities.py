"""Load Puerto Rico's 78 municipios from Census TIGER/Line shapefiles.

Downloads the official 2023 vintage COUNTY file (in Puerto Rico, US "counties"
are the municipios). Extracts geometries, normalizes names, computes centroids +
area, and upserts into the `municipalities` table.

Run:
    cd etl && uv run python -m sources.census_tiger_municipalities
"""

from __future__ import annotations

import unicodedata
import zipfile
from pathlib import Path

import geopandas as gpd
import requests
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential

from lib.db import session_scope
from lib.logging import get_logger
from lib.settings import settings
from lib.tracker import EtlRunTracker

log = get_logger(__name__)

# In Puerto Rico, US Census "counties" ARE the municipios. FIPS state code = 72.
TIGER_COUNTY_URL = "https://www2.census.gov/geo/tiger/TIGER2023/COUNTY/tl_2023_us_county.zip"
PR_STATE_FIPS = "72"

SOURCE_SLUG = "census_tiger_pr"


def _normalize_name(name: str) -> str:
    """Lowercase + strip accents for searchable names."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_only.lower().strip()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _download(url: str, dest: Path) -> Path:
    """Download to `dest`. Caches — skips if file already exists."""
    if dest.exists():
        log.info("Cached: %s", dest.name)
        return dest
    log.info("Downloading %s ...", url)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                f.write(chunk)
    log.info("Saved %d bytes -> %s", dest.stat().st_size, dest)
    return dest


def _extract(zip_path: Path) -> Path:
    """Extract zip to a sibling directory and return the extracted dir."""
    out_dir = zip_path.with_suffix("")
    if out_dir.exists() and any(out_dir.iterdir()):
        log.info("Already extracted: %s", out_dir.name)
        return out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    log.info("Extracted to %s", out_dir)
    return out_dir


def load_pr_municipalities() -> gpd.GeoDataFrame:
    """Download TIGER county data and return a GeoDataFrame of PR municipios in EPSG:4326."""
    raw = settings.raw_dir / "census_tiger"
    raw.mkdir(parents=True, exist_ok=True)

    county_zip = _download(TIGER_COUNTY_URL, raw / "tl_2023_us_county.zip")
    county_dir = _extract(county_zip)

    shp = next(county_dir.glob("*.shp"))
    log.info("Reading shapefile: %s", shp.name)
    gdf = gpd.read_file(shp)
    log.info("Loaded %d features from TIGER (all US)", len(gdf))

    # Filter to Puerto Rico (FIPS state '72')
    gdf = gdf[gdf["STATEFP"].astype(str) == PR_STATE_FIPS].copy()
    log.info("Filtered to %d features for Puerto Rico (STATEFP=%s)", len(gdf), PR_STATE_FIPS)

    # Ensure WGS84
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # GEOID for counties = STATEFP + COUNTYFP (e.g. "72127" for San Juan)
    gdf["muni_id"] = gdf["GEOID"].astype(str)
    gdf["name"] = gdf["NAME"].astype(str)
    gdf["name_normalized"] = gdf["name"].map(_normalize_name)

    # Compute area in km² using an equal-area projection (EPSG:6933)
    area_m2 = gdf.to_crs(epsg=6933).geometry.area
    gdf["area_sq_km"] = (area_m2 / 1_000_000).round(2)

    # Representative point (guaranteed inside the polygon) for map labels
    gdf["centroid_wkt"] = gdf.geometry.representative_point().to_wkt()

    # Ensure geometry is MultiPolygon (schema requires it)
    gdf["geometry"] = gdf.geometry.apply(
        lambda g: g if g.geom_type == "MultiPolygon" else gpd.GeoSeries([g]).union_all()
    )

    log.info("Processed %d PR municipios", len(gdf))
    if len(gdf) != 78:
        log.warning("Expected 78 municipios, got %d — investigate!", len(gdf))

    return gdf.reset_index(drop=True)


UPSERT_SQL = text(
    """
    INSERT INTO municipalities (
        id, name, name_normalized, geometry, centroid, area_sq_km, updated_at
    )
    VALUES (
        :id, :name, :name_normalized,
        ST_Multi(ST_GeomFromText(:geometry_wkt, 4326)),
        ST_GeogFromText(:centroid_wkt),
        :area_sq_km,
        now()
    )
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        name_normalized = EXCLUDED.name_normalized,
        geometry = EXCLUDED.geometry,
        centroid = EXCLUDED.centroid,
        area_sq_km = EXCLUDED.area_sq_km,
        updated_at = now()
    """
)


def main() -> None:
    with EtlRunTracker(source_slug=SOURCE_SLUG) as run:
        gdf = load_pr_municipalities()
        run.rows_read = len(gdf)

        upserted = 0
        with session_scope() as s:
            for _, row in gdf.iterrows():
                s.execute(
                    UPSERT_SQL,
                    {
                        "id": row["muni_id"],
                        "name": row["name"],
                        "name_normalized": row["name_normalized"],
                        "geometry_wkt": row.geometry.wkt,
                        "centroid_wkt": "SRID=4326;" + row["centroid_wkt"],
                        "area_sq_km": float(row["area_sq_km"]),
                    },
                )
                upserted += 1
        run.rows_upserted = upserted
        log.info("Upserted %d municipalities", upserted)


if __name__ == "__main__":
    main()
