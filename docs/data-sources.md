# Data Sources

Every dataset used in SaludPR is publicly available and traceable. This document is the source of truth — when in doubt, check here.

Last updated: *TBD at first data pull*

---

## 1. CDC Behavioral Risk Factor Surveillance System (BRFSS)

- **What:** Self-reported prevalence of chronic conditions (diabetes, hypertension, asthma, obesity) by state/territory.
- **Geography:** Puerto Rico (territory-level; some county/municipality breakouts limited).
- **Update frequency:** Annual (typically 12-18 month lag).
- **Source:** https://www.cdc.gov/brfss/annual_data/annual_data.htm
- **License:** Public domain (U.S. federal government data).
- **Known limitations:**
  - Self-reported — actual clinical prevalence often higher.
  - Inconsistent collection in Puerto Rico historically (see Public Health Post, 2024).
  - Sample sizes small for some municipalities; we'll suppress cells below CDC thresholds.

## 2. HRSA Medically Underserved Areas / Populations (MUA/P)

- **What:** Federal designation of medically underserved areas + health professional shortage areas (HPSA).
- **Geography:** Municipality level for Puerto Rico.
- **Update frequency:** Rolling; revised as designations change.
- **Source:** https://data.hrsa.gov/tools/shortage-area/mua-find
- **License:** Public domain.
- **Known limitations:**
  - Designations lag underlying reality.
  - Nearly all 78 PR municipalities currently designated MUA; variance between them is subtle.

## 3. U.S. Census Bureau — American Community Survey (ACS) + PR Community Survey

- **What:** Demographics, poverty rate, insurance coverage, age distribution, household composition.
- **Geography:** Municipality, census tract.
- **Update frequency:** Annual (5-year rolling estimates).
- **Source:** https://data.census.gov / https://www.census.gov/programs-surveys/acs
- **License:** Public domain.

## 4. Census Bureau — Community Resilience Estimates for Puerto Rico

- **What:** Social vulnerability index by municipality and census tract, including disaster risk overlay (FEMA National Risk Index).
- **Geography:** Municipality + census tract.
- **Update frequency:** Annual.
- **Source:** https://www.census.gov/programs-surveys/community-resilience-estimates/data/cre-puerto-rico.html
- **License:** Public domain.

## 5. Puerto Rico Department of Health (PRDOH)

- **What:** Hospital registry, licensed facilities, vital statistics.
- **Geography:** Island-wide with municipality detail.
- **Update frequency:** Varies by dataset.
- **Source:** https://www.salud.pr.gov / https://estadisticas.pr.gov
- **License:** Commonwealth of Puerto Rico public data.
- **Known limitations:**
  - Data portals are inconsistent; some datasets require manual extraction.
  - Language: primarily Spanish.

## 6. CMS — Medicare Provider Data + Hospital Compare

- **What:** Medicare-certified hospital information, bed counts, quality measures.
- **Geography:** Facility-level, with municipality mapping.
- **Update frequency:** Quarterly.
- **Source:** https://data.cms.gov
- **License:** Public domain.

## 7. HRSA Area Health Resources File (AHRF)

- **What:** County-level health resources, provider counts, hospital capacity.
- **Geography:** Equivalent of municipality for PR.
- **Update frequency:** Annual.
- **Source:** https://data.hrsa.gov/topics/health-workforce/ahrf
- **License:** Public domain.

## 8. PR TIGER/Line shapefiles (Census)

- **What:** Geographic boundaries for Puerto Rico municipalities + census tracts.
- **Geography:** Municipality + tract.
- **Source:** https://www.census.gov/cgi-bin/geo/shapefiles/index.php
- **License:** Public domain.

---

## Data we intentionally do NOT use

- **Private claims data** — HIPAA exposure, not publicly replicable.
- **Individual patient records** — privacy risk, not aggregated.
- **Scraped social media health claims** — unreliable, ethically gray.

---

## How we handle conflicts between sources

When two public sources disagree (e.g., CDC BRFSS vs. PRDOH diabetes estimates):

1. Show both on the dashboard with clear source labels.
2. Explain the methodological difference in a tooltip or footnote.
3. Default to the federal source for cross-state comparisons; default to PRDOH for PR-only analysis.

---

## Methodology notes

- **Suppression:** Counts under CDC thresholds are suppressed to protect privacy.
- **Smoothing:** Where year-over-year sample variance is high, we may present 3-year rolling averages (labeled as such).
- **Interpolation:** We do NOT interpolate missing municipality values. Missing is shown as "No data available."
- **Age-adjustment:** Rates are age-adjusted to the 2000 U.S. standard population where applicable (labeled).
