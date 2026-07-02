/**
 * Indicator metadata — human labels, formatting, color direction.
 *
 * direction:
 *   'high_is_bad'  — higher = worse (poverty, uninsured) — use warm/alert palette
 *   'high_is_good' — higher = better (education, checkup)  — use cool/calm palette
 *   'neutral'      — demographic (population, median age)  — use sequential neutral
 */

export type IndicatorDirection =
  | "high_is_bad"
  | "high_is_good"
  | "low_is_bad"
  | "neutral";

export type IndicatorMeta = {
  code: string;
  label_en: string;
  label_es: string;
  short_es: string;
  short_en: string;
  unit: "percent" | "dollars" | "count" | "years";
  direction: IndicatorDirection;
  description_es?: string;
};

export const INDICATORS: Record<string, IndicatorMeta> = {
  pct_below_poverty: {
    code: "pct_below_poverty",
    label_en: "Population below poverty line",
    label_es: "Población bajo el umbral de pobreza",
    short_en: "Poverty",
    short_es: "Pobreza",
    unit: "percent",
    direction: "high_is_bad",
    description_es:
      "Porcentaje de residentes bajo el nivel federal de pobreza (ACS B17001).",
  },
  pct_uninsured: {
    code: "pct_uninsured",
    label_en: "Adults without health insurance",
    label_es: "Adultos sin cobertura de salud",
    short_en: "Uninsured",
    short_es: "Sin seguro",
    unit: "percent",
    direction: "high_is_bad",
    description_es:
      "Porcentaje sin cobertura de salud (ACS B27010).",
  },
  pct_no_high_school: {
    code: "pct_no_high_school",
    label_en: "Adults without high school",
    label_es: "Adultos sin diploma de escuela superior",
    short_en: "No HS diploma",
    short_es: "Sin diploma",
    unit: "percent",
    direction: "high_is_bad",
  },
  pct_bachelors_or_higher: {
    code: "pct_bachelors_or_higher",
    label_en: "Adults with bachelor's degree or higher",
    label_es: "Adultos con bachillerato o más",
    short_en: "Bachelor's+",
    short_es: "Bachillerato+",
    unit: "percent",
    direction: "high_is_good",
  },
  pct_overcrowded_housing: {
    code: "pct_overcrowded_housing",
    label_en: "Housing units with >1 occupant per room",
    label_es: "Viviendas con >1 ocupante por cuarto",
    short_en: "Overcrowded",
    short_es: "Hacinamiento",
    unit: "percent",
    direction: "high_is_bad",
  },
  pct_age_65_plus: {
    code: "pct_age_65_plus",
    label_en: "Population age 65+",
    label_es: "Población de 65 años o más",
    short_en: "Age 65+",
    short_es: "65+ años",
    unit: "percent",
    direction: "neutral",
  },
  pct_under_18: {
    code: "pct_under_18",
    label_en: "Population under 18",
    label_es: "Población menor de 18",
    short_en: "Under 18",
    short_es: "Menor de 18",
    unit: "percent",
    direction: "neutral",
  },
  median_age: {
    code: "median_age",
    label_en: "Median age",
    label_es: "Edad mediana",
    short_en: "Median age",
    short_es: "Edad mediana",
    unit: "years",
    direction: "neutral",
  },
  median_household_income: {
    code: "median_household_income",
    label_en: "Median household income",
    label_es: "Ingreso mediano por hogar",
    short_en: "Median income",
    short_es: "Ingreso mediano",
    unit: "dollars",
    direction: "high_is_good",
  },
  total_population: {
    code: "total_population",
    label_en: "Total population",
    label_es: "Población total",
    short_en: "Population",
    short_es: "Población",
    unit: "count",
    direction: "neutral",
  },
  imu_score: {
    code: "imu_score",
    label_en: "HRSA Index of Medical Underservice",
    label_es: "Índice de escasez médica (HRSA)",
    short_en: "IMU Score",
    short_es: "IMU Score",
    unit: "count",
    direction: "low_is_bad",
    description_es:
      "Puntuación federal 0-100. Menor = mayor escasez médica. Umbral: 62.",
  },
};

/**
 * Color ramps (low → high), 5 stops each.
 * Single-hue, lightness-monotone ramps: every step keeps ≥2:1 contrast against
 * the map background (#0e1d24) so the low end never reads as "no data", and
 * the brand amber stays out of the data layer (it marks UI, not magnitude).
 * High-is-bad uses rose (the token reserved for critical data); high-is-good
 * uses teal; neutral uses cool gray.
 */
export const COLOR_RAMPS: Record<IndicatorDirection, string[]> = {
  high_is_bad: ["#7d3c4d", "#9e4f60", "#c06371", "#e17b85", "#ff9d9f"],
  high_is_good: ["#1a5f5e", "#12796e", "#149282", "#3bbca6", "#72f0da"],
  // For low_is_bad: low values rose (bad), high values recede. Reverse of
  // high_is_bad so "worse" is always the brighter end of the same hue.
  low_is_bad: ["#ff9d9f", "#e17b85", "#c06371", "#9e4f60", "#7d3c4d"],
  neutral: ["#41565e", "#5a6f77", "#748a91", "#90a6ac", "#b6c7cb"],
};

export function formatValue(value: number | null, unit: IndicatorMeta["unit"], locale = "es"): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return locale === "es" ? "sin datos" : "no data";
  }
  if (unit === "percent") {
    return `${value.toFixed(1)}%`;
  }
  if (unit === "dollars") {
    return new Intl.NumberFormat(locale === "es" ? "es-PR" : "en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(value);
  }
  if (unit === "years") {
    return locale === "es" ? `${value.toFixed(1)} años` : `${value.toFixed(1)} yr`;
  }
  return new Intl.NumberFormat(locale === "es" ? "es-PR" : "en-US").format(
    Math.round(value),
  );
}

/**
 * Compute quintile breakpoints (5 buckets) from a list of numeric values.
 * Returns 6 numbers: [min, q1, q2, q3, q4, max].
 */
export function quintileBreaks(values: number[]): number[] {
  if (values.length === 0) return [0, 0, 0, 0, 0, 0];
  const sorted = [...values].sort((a, b) => a - b);
  const n = sorted.length;
  const pickSafe = (idx: number) => sorted[Math.min(Math.max(idx, 0), n - 1)] ?? 0;
  return [
    sorted[0] ?? 0,
    pickSafe(Math.floor(n * 0.2)),
    pickSafe(Math.floor(n * 0.4)),
    pickSafe(Math.floor(n * 0.6)),
    pickSafe(Math.floor(n * 0.8)),
    sorted[n - 1] ?? 0,
  ];
}
