"""Load Puerto Rico's barrios (~900) from Census TIGER/Line COUSUB shapefile.

In PR, Census "county subdivisions" = barrios. The file was already downloaded
by an earlier run of census_tiger_municipalities (when we accidentally used
COUSUB first). If not present, this loader will download it.

IDs are 10-digit Census GEOIDs: state(2) + county(3) + cousub(5).
Parent municipio FK is the first 5 digits.

Run:
    cd etl && uv run python -m sources.census_tiger_barrios
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

TIGER_COUSUB_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2023/COUSUB/tl_2023_72_cousub.zip"
)
SOURCE_SLUG = "census_tiger_pr"


def _normalize_name(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_only.lower().strip()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _download(url: str, dest: Path) -> Path:
    if dest.exists():
        log.info("Cached: %s", dest.name)
        return dest
    log.info("Downloading %s ...", url)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                f.write(chunk)
    return dest


def _extract(zip_path: Path) -> Path:
    out_dir = zip_path.with_suffix("")
    if out_dir.exists() and any(out_dir.iterdir()):
        return out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    return out_dir


def load_pr_barrios() -> gpd.GeoDataFrame:
    raw = settings.raw_dir / "census_tiger"
    raw.mkdir(parents=True, exist_ok=True)

    cousub_zip = _download(TIGER_COUSUB_URL, raw / "tl_2023_72_cousub.zip")
    cousub_dir = _extract(cousub_zip)

    shp = next(cousub_dir.glob("*.shp"))
    log.info("Reading shapefile: %s", shp.name)
    gdf = gpd.read_file(shp)
    log.info("Loaded %d features", len(gdf))

    # Ensure WGS84
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # GEOID is state(2) + county(3) + cousub(5) = 10 digits, e.g. "7212735560"
    gdf["barrio_id"] = gdf["GEOID"].astype(str).str.zfill(10)
    gdf["muni_id"] = gdf["barrio_id"].str.slice(0, 5)
    gdf["name"] = gdf["NAME"].astype(str)
    gdf["name_normalized"] = gdf["name"].map(_normalize_name)

    # Dedupe on barrio_id (just in case)
    gdf = gdf.drop_duplicates(subset=["barrio_id"]).reset_index(drop=True)

    # Area in km² using equal-area projection
    area_m2 = gdf.to_crs(epsg=6933).geometry.area
    gdf["area_sq_km"] = (area_m2 / 1_000_000).round(2)

    # Representative point for labels
    gdf["centroid_wkt"] = gdf.geometry.representative_point().to_wkt()

    # Ensure MultiPolygon
    gdf["geometry"] = gdf.geometry.apply(
        lambda g: g if g.geom_type == "MultiPolygon" else gpd.GeoSeries([g]).union_all()
    )

    log.info("Processed %d barrios across %d munis",
             len(gdf), gdf["muni_id"].nunique())
    return gdf


UPSERT_SQL = text(
    """
    INSERT INTO barrios (
        id, muni_id, name, name_normalized,
        geometry, centroid, area_sq_km, updated_at
    )
    VALUES (
        :id, :muni_id, :name, :name_normalized,
        ST_Multi(ST_GeomFromText(:geometry_wkt, 4326)),
        ST_GeogFromText(:centroid_wkt),
        :area_sq_km,
        now()
    )
    ON CONFLICT (id) DO UPDATE SET
        muni_id = EXCLUDED.muni_id,
        name = EXCLUDED.name,
        name_normalized = EXCLUDED.name_normalized,
        geometry = EXCLUDED.geometry,
        centroid = EXCLUDED.centroid,
        area_sq_km = EXCLUDED.area_sq_km,
        updated_at = now()
    """
)


def _get_known_munis() -> set[str]:
    with session_scope() as s:
        rows = s.execute(text("SELECT id FROM municipalities")).all()
    return {r[0] for r in rows}


def main() -> None:
    known_munis = _get_known_munis()
    if not known_munis:
        raise RuntimeError("No municipalities in DB. Run the TIGER muni loader first.")

    with EtlRunTracker(source_slug=SOURCE_SLUG) as run:
        gdf = load_pr_barrios()
        run.rows_read = len(gdf)

        upserted = 0
        skipped = 0
        with session_scope() as s:
            for _, row in gdf.iterrows():
                if row["muni_id"] not in known_munis:
                    skipped += 1
                    continue
                s.execute(
                    UPSERT_SQL,
                    {
                        "id": row["barrio_id"],
                        "muni_id": row["muni_id"],
                        "name": row["name"],
                        "name_normalized": row["name_normalized"],
                        "geometry_wkt": row.geometry.wkt,
                        "centroid_wkt": "SRID=4326;" + row["centroid_wkt"],
                        "area_sq_km": float(row["area_sq_km"]),
                    },
                )
                upserted += 1

        run.rows_upserted = upserted
        run.rows_skipped = skipped
        log.info("Upserted %d barrios (skipped %d with unknown muni)", upserted, skipped)


if __name__ == "__main__":
    main()
