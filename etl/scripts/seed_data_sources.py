"""Seed `data_sources` table with the public datasets SaludPR uses.

Idempotent: safe to run multiple times. Uses INSERT ... ON CONFLICT DO UPDATE
so descriptions stay in sync with the canonical list here.

Run:
    cd etl && uv run python scripts/seed_data_sources.py
"""

from __future__ import annotations

from sqlalchemy import text

from lib.db import session_scope
from lib.logging import get_logger

log = get_logger(__name__)

SOURCES: list[dict[str, str | None]] = [
    {
        "slug": "census_tiger_pr",
        "name": "US Census TIGER/Line Shapefiles — Puerto Rico Municipalities",
        "organization": "U.S. Census Bureau",
        "url": "https://www.census.gov/cgi-bin/geo/shapefiles/index.php",
        "license": "Public Domain (US Federal)",
        "update_frequency": "Annual",
        "description_en": (
            "Official geographic boundaries for Puerto Rico's 78 municipios "
            "and census tracts. Used as the base layer for every map."
        ),
        "description_es": (
            "Límites geográficos oficiales de los 78 municipios de Puerto Rico "
            "y tractos censales. Base de todos los mapas."
        ),
        "known_limitations": (
            "Boundaries can shift slightly between vintages; we use a single "
            "year consistently to avoid spurious changes."
        ),
    },
    {
        "slug": "cdc_brfss",
        "name": "CDC Behavioral Risk Factor Surveillance System",
        "organization": "Centers for Disease Control and Prevention",
        "url": "https://www.cdc.gov/brfss/annual_data/annual_data.htm",
        "license": "Public Domain (US Federal)",
        "update_frequency": "Annual",
        "description_en": (
            "Telephone-based survey of chronic disease prevalence and health "
            "behaviors. Main source for diabetes, hypertension, and asthma rates."
        ),
        "description_es": (
            "Encuesta telefónica sobre prevalencia de enfermedades crónicas y "
            "comportamientos de salud. Fuente principal para diabetes, "
            "hipertensión y asma."
        ),
        "known_limitations": (
            "Self-reported; actual clinical prevalence is typically higher. "
            "Inconsistently collected in Puerto Rico historically."
        ),
    },
    {
        "slug": "hrsa_mua",
        "name": "HRSA Medically Underserved Areas / Populations",
        "organization": "Health Resources and Services Administration",
        "url": "https://data.hrsa.gov/tools/shortage-area/mua-find",
        "license": "Public Domain (US Federal)",
        "update_frequency": "Rolling",
        "description_en": (
            "Federal designation of medically underserved areas and health "
            "professional shortage areas (HPSA)."
        ),
        "description_es": (
            "Designación federal de áreas médicamente desatendidas y áreas con "
            "escasez de profesionales de salud."
        ),
        "known_limitations": (
            "Designations can lag underlying reality by years. Nearly all 78 "
            "PR municipalities are currently designated; variance is subtle."
        ),
    },
    {
        "slug": "census_acs",
        "name": "Census American Community Survey + PR Community Survey",
        "organization": "U.S. Census Bureau",
        "url": "https://data.census.gov",
        "license": "Public Domain (US Federal)",
        "update_frequency": "Annual (5-year rolling estimates)",
        "description_en": (
            "Demographics, poverty rates, insurance coverage, age distribution. "
            "Denominator for many per-capita calculations."
        ),
        "description_es": (
            "Demografía, tasas de pobreza, cobertura de seguro, distribución por "
            "edad. Denominador para cálculos per cápita."
        ),
        "known_limitations": None,
    },
    {
        "slug": "census_cre",
        "name": "Census Community Resilience Estimates for Puerto Rico",
        "organization": "U.S. Census Bureau",
        "url": "https://www.census.gov/programs-surveys/community-resilience-estimates/data/cre-puerto-rico.html",
        "license": "Public Domain (US Federal)",
        "update_frequency": "Annual",
        "description_en": (
            "Social vulnerability index by municipality and census tract, with "
            "FEMA National Risk Index disaster-risk overlay."
        ),
        "description_es": (
            "Índice de vulnerabilidad social por municipio y tracto censal, con "
            "superposición de riesgo de desastres del FEMA NRI."
        ),
        "known_limitations": None,
    },
    {
        "slug": "prdoh",
        "name": "Puerto Rico Department of Health",
        "organization": "Departamento de Salud de Puerto Rico",
        "url": "https://www.salud.pr.gov",
        "license": "Commonwealth of Puerto Rico Public Data",
        "update_frequency": "Varies by dataset",
        "description_en": (
            "Hospital registry, licensed facilities, vital statistics. "
            "Local source for island-specific data."
        ),
        "description_es": (
            "Registro de hospitales, facilidades licenciadas, estadísticas "
            "vitales. Fuente local de datos específicos de la isla."
        ),
        "known_limitations": (
            "Data portals are inconsistent; some datasets require manual "
            "extraction. Primarily Spanish."
        ),
    },
    {
        "slug": "cms_provider",
        "name": "CMS Medicare Provider Data + Hospital Compare",
        "organization": "Centers for Medicare & Medicaid Services",
        "url": "https://data.cms.gov",
        "license": "Public Domain (US Federal)",
        "update_frequency": "Quarterly",
        "description_en": (
            "Medicare-certified hospital information, bed counts, quality "
            "measures."
        ),
        "description_es": (
            "Información de hospitales certificados por Medicare, conteo de "
            "camas, medidas de calidad."
        ),
        "known_limitations": None,
    },
    {
        "slug": "hrsa_ahrf",
        "name": "HRSA Area Health Resources File",
        "organization": "Health Resources and Services Administration",
        "url": "https://data.hrsa.gov/topics/health-workforce/ahrf",
        "license": "Public Domain (US Federal)",
        "update_frequency": "Annual",
        "description_en": (
            "County/municipality-level health resources, provider counts, "
            "hospital capacity."
        ),
        "description_es": (
            "Recursos de salud a nivel de municipio, conteo de proveedores, "
            "capacidad hospitalaria."
        ),
        "known_limitations": None,
    },
]

UPSERT_SQL = text(
    """
    INSERT INTO data_sources (
        slug, name, organization, url, license,
        update_frequency, description_en, description_es, known_limitations
    )
    VALUES (
        :slug, :name, :organization, :url, :license,
        :update_frequency, :description_en, :description_es, :known_limitations
    )
    ON CONFLICT (slug) DO UPDATE SET
        name = EXCLUDED.name,
        organization = EXCLUDED.organization,
        url = EXCLUDED.url,
        license = EXCLUDED.license,
        update_frequency = EXCLUDED.update_frequency,
        description_en = EXCLUDED.description_en,
        description_es = EXCLUDED.description_es,
        known_limitations = EXCLUDED.known_limitations
    """
)


def main() -> None:
    log.info("Seeding %d data sources...", len(SOURCES))
    with session_scope() as s:
        for source in SOURCES:
            s.execute(UPSERT_SQL, source)
            log.info("  upserted: %s", source["slug"])
    log.info("Done.")


if __name__ == "__main__":
    main()
