"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Map, {
  Source,
  Layer,
  type LayerProps,
  type MapRef,
} from "react-map-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import {
  INDICATORS,
  COLOR_RAMPS,
  formatValue,
  quintileBreaks,
} from "@/lib/indicators";

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? "";

/** Barrio population below this = statistically noisy, fade + warn. */
const RELIABLE_POP_THRESHOLD = 1000;

type MuniFeatureProps = {
  id: string;
  name: string;
  area_sq_km: number | null;
  population_latest: number | null;
  value: number | null;
  value_type: string | null;
  year: number | null;
  is_suppressed: boolean | null;
  is_estimated: boolean | null;
};

type BarrioFeatureProps = MuniFeatureProps & {
  muni_id: string;
};

type GeoFeatureMuni = GeoJSON.Feature<GeoJSON.Geometry, MuniFeatureProps>;
type GeoFeatureBarrio = GeoJSON.Feature<GeoJSON.Geometry, BarrioFeatureProps>;

type HoverInfo = {
  id: string;
  name: string;
  value: number | null;
  population: number | null;
  x: number;
  y: number;
  reliable: boolean;
};

type ViewState = "island" | "muni";

type Props = {
  indicator: string;
  year: number;
  onBreaksComputed?: (breaks: number[]) => void;
  onMuniSelected?: (muniName: string | null) => void;
};

/** Traverse a geometry's coordinates to find a bounding box. */
function geometryBounds(
  geom: GeoJSON.Geometry,
): [[number, number], [number, number]] {
  let minX = Infinity,
    minY = Infinity,
    maxX = -Infinity,
    maxY = -Infinity;

  const walk = (coords: unknown): void => {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === "number" && typeof coords[1] === "number") {
      const [x, y] = coords as [number, number];
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
      return;
    }
    for (const c of coords) walk(c);
  };

  walk((geom as GeoJSON.Polygon | GeoJSON.MultiPolygon).coordinates);
  return [
    [minX, minY],
    [maxX, maxY],
  ];
}

export function PRMap({
  indicator,
  year,
  onBreaksComputed,
  onMuniSelected,
}: Props) {
  const mapRef = useRef<MapRef>(null);

  // --- View state ---
  const [viewState, setViewState] = useState<ViewState>("island");
  const [selectedMuniId, setSelectedMuniId] = useState<string | null>(null);
  const [selectedMuniName, setSelectedMuniName] = useState<string | null>(null);

  // --- Data ---
  const [muniGeojson, setMuniGeojson] =
    useState<GeoJSON.FeatureCollection | null>(null);
  const [barrioGeojson, setBarrioGeojson] =
    useState<GeoJSON.FeatureCollection | null>(null);
  const [error, setError] = useState<string | null>(null);

  // --- Hover ---
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [hoverSource, setHoverSource] = useState<"munis" | "barrios" | null>(
    null,
  );
  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);

  const meta = INDICATORS[indicator];

  // --- Fetch muni data whenever indicator/year changes ---
  useEffect(() => {
    let cancelled = false;
    setMuniGeojson(null);

    const url = new URL("/api/municipalities", window.location.origin);
    url.searchParams.set("indicator", indicator);
    url.searchParams.set("year", String(year));

    fetch(url.toString())
      .then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json() as Promise<GeoJSON.FeatureCollection>;
      })
      .then((data) => {
        if (!cancelled) setMuniGeojson(data);
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load map data");
      });

    return () => {
      cancelled = true;
    };
  }, [indicator, year]);

  // --- Fetch barrio data when a muni is selected ---
  useEffect(() => {
    if (!selectedMuniId) {
      setBarrioGeojson(null);
      return;
    }
    let cancelled = false;

    const url = new URL("/api/barrios", window.location.origin);
    url.searchParams.set("muni_id", selectedMuniId);
    url.searchParams.set("indicator", indicator);
    url.searchParams.set("year", String(year));

    fetch(url.toString())
      .then((r) => {
        if (!r.ok) throw new Error(`Barrios API ${r.status}`);
        return r.json() as Promise<GeoJSON.FeatureCollection>;
      })
      .then((data) => {
        if (!cancelled) setBarrioGeojson(data);
      })
      .catch(() => void 0);

    return () => {
      cancelled = true;
    };
  }, [selectedMuniId, indicator, year]);

  // --- Compute muni-scale quintile breaks (for island view legend) ---
  const muniBreaks = useMemo<number[] | null>(() => {
    if (!muniGeojson) return null;
    const values = (muniGeojson.features as GeoFeatureMuni[])
      .map((f) => f.properties.value)
      .filter((v): v is number => v !== null && v !== undefined);
    if (values.length === 0) return null;
    return quintileBreaks(values);
  }, [muniGeojson]);

  // --- Compute barrio-scale quintile breaks (for muni-zoom view) ---
  const barrioBreaks = useMemo<number[] | null>(() => {
    if (!barrioGeojson) return null;
    const values = (barrioGeojson.features as GeoFeatureBarrio[])
      .map((f) => f.properties.value)
      .filter((v): v is number => v !== null && v !== undefined);
    if (values.length === 0) return null;
    return quintileBreaks(values);
  }, [barrioGeojson]);

  // Active breaks = whichever view we're in
  const activeBreaks = viewState === "muni" ? barrioBreaks : muniBreaks;

  // Notify parent of breaks for shared legend
  useEffect(() => {
    if (activeBreaks) onBreaksComputed?.(activeBreaks);
  }, [activeBreaks, onBreaksComputed]);

  // Notify parent of muni selection (so it can render a header)
  useEffect(() => {
    onMuniSelected?.(selectedMuniName);
  }, [selectedMuniName, onMuniSelected]);

  // --- Paint expressions ---
  const ramp = COLOR_RAMPS[meta?.direction ?? "neutral"];
  const noData = "#0e1d24";

  const buildStepColor = (breaks: number[] | null): mapboxgl.FillPaint["fill-color"] => {
    if (!breaks) return noData;
    return [
      "case",
      ["==", ["get", "value"], null],
      noData,
      [
        "step",
        ["to-number", ["get", "value"]],
        ramp[0],
        breaks[1] ?? 0, ramp[1],
        breaks[2] ?? 0, ramp[2],
        breaks[3] ?? 0, ramp[3],
        breaks[4] ?? 0, ramp[4],
      ],
    ];
  };

  // Muni fill layer — dimmed when a muni is selected
  const muniFillLayer: LayerProps = {
    id: "municipalities-fill",
    type: "fill",
    paint: {
      "fill-color": buildStepColor(muniBreaks),
      "fill-opacity":
        viewState === "muni"
          ? [
              "case",
              ["==", ["get", "id"], selectedMuniId ?? ""],
              0.0,  // Hide the selected muni so barrios show through
              0.15, // Other munis stay dim for context
            ]
          : [
              "case",
              ["boolean", ["feature-state", "hover"], false],
              0.95,
              0.78,
            ],
    },
  };

  const muniLineLayer: LayerProps = {
    id: "municipalities-line",
    type: "line",
    paint: {
      "line-color": "#0a1519",
      "line-width": 0.4,
      "line-opacity": viewState === "muni" ? 0.25 : 0.6,
    },
  };

  const muniHighlightLineLayer: LayerProps = {
    id: "municipalities-line-highlight",
    type: "line",
    paint: {
      "line-color": "#f59e0b",
      "line-width":
        viewState === "muni"
          ? [
              "case",
              ["==", ["get", "id"], selectedMuniId ?? ""],
              2.0,
              0,
            ]
          : [
              "case",
              ["boolean", ["feature-state", "hover"], false],
              2.5,
              0,
            ],
    },
  };

  // Barrio fill layer — faded when pop < threshold
  const barrioFillLayer: LayerProps = {
    id: "barrios-fill",
    type: "fill",
    paint: {
      "fill-color": buildStepColor(barrioBreaks),
      "fill-opacity": [
        "case",
        ["boolean", ["feature-state", "hover"], false],
        0.98,
        [
          "case",
          [
            "<",
            ["coalesce", ["get", "population_latest"], 99999],
            RELIABLE_POP_THRESHOLD,
          ],
          0.35, // low-population barrios are faded
          0.82,
        ],
      ],
    },
  };

  const barrioLineLayer: LayerProps = {
    id: "barrios-line",
    type: "line",
    paint: {
      "line-color": "#1e3640",
      "line-width": 0.6,
      "line-opacity": 0.8,
    },
  };

  const barrioHighlightLineLayer: LayerProps = {
    id: "barrios-line-highlight",
    type: "line",
    paint: {
      "line-color": "#fcd34d",
      "line-width": [
        "case",
        ["boolean", ["feature-state", "hover"], false],
        2.0,
        0,
      ],
    },
  };

  // --- Interactive layers list ---
  const interactiveLayers =
    viewState === "muni"
      ? ["barrios-fill", "municipalities-fill"]
      : ["municipalities-fill"];

  // --- Click handler: drill into a muni ---
  const handleMapClick = useCallback(
    (e: mapboxgl.MapLayerMouseEvent) => {
      if (viewState === "muni") return; // click-back handled by the header button

      const feat = e.features?.[0] as GeoFeatureMuni | undefined;
      if (!feat) return;

      const id = String(feat.properties.id);
      const name = feat.properties.name;

      // Compute bounds for zoom
      const bounds = geometryBounds(feat.geometry);

      setSelectedMuniId(id);
      setSelectedMuniName(name);
      setViewState("muni");

      // Zoom the map
      mapRef.current?.fitBounds(bounds, {
        padding: { top: 80, bottom: 80, left: 80, right: 80 },
        duration: 900,
        maxZoom: 13,
      });
    },
    [viewState],
  );

  // --- Back to island view ---
  const handleZoomOut = useCallback(() => {
    setViewState("island");
    setSelectedMuniId(null);
    setSelectedMuniName(null);
    setBarrioGeojson(null);
    setHoverId(null);
    setHoverSource(null);
    setHoverInfo(null);

    mapRef.current?.flyTo({
      center: [-66.45, 18.22],
      zoom: 8.5,
      duration: 900,
    });
  }, []);

  // Expose back-handler to parent via window event (simpler than prop plumbing)
  useEffect(() => {
    const handler = () => handleZoomOut();
    window.addEventListener("saludpr:zoom-out", handler);
    return () => window.removeEventListener("saludpr:zoom-out", handler);
  }, [handleZoomOut]);

  const handleMouseMove = useCallback(
    (e: mapboxgl.MapLayerMouseEvent) => {
      const feat = e.features?.[0];
      if (!feat) {
        if (hoverId !== null && hoverSource) {
          mapRef.current?.setFeatureState(
            { source: hoverSource, id: hoverId },
            { hover: false },
          );
        }
        setHoverId(null);
        setHoverSource(null);
        setHoverInfo(null);
        return;
      }

      const sourceLayer = feat.layer.id.startsWith("barrios") ? "barrios" : "munis";
      const props = feat.properties as MuniFeatureProps & { population_latest: number | null };
      const id = String(props.id);

      if (id !== hoverId || sourceLayer !== hoverSource) {
        if (hoverId !== null && hoverSource) {
          mapRef.current?.setFeatureState(
            { source: hoverSource, id: hoverId },
            { hover: false },
          );
        }
        mapRef.current?.setFeatureState(
          { source: sourceLayer, id },
          { hover: true },
        );
        setHoverId(id);
        setHoverSource(sourceLayer);
      }

      const pop = props.population_latest;
      setHoverInfo({
        id,
        name: props.name,
        value: props.value,
        population: pop,
        x: e.point.x,
        y: e.point.y,
        reliable: pop === null || pop >= RELIABLE_POP_THRESHOLD,
      });
    },
    [hoverId, hoverSource],
  );

  const handleMouseLeave = useCallback(() => {
    if (hoverId !== null && hoverSource) {
      mapRef.current?.setFeatureState(
        { source: hoverSource, id: hoverId },
        { hover: false },
      );
    }
    setHoverId(null);
    setHoverSource(null);
    setHoverInfo(null);
  }, [hoverId, hoverSource]);

  // --- Early returns ---
  if (!MAPBOX_TOKEN) {
    return (
      <div className="flex h-[560px] items-center justify-center bg-[var(--color-surface)] text-center">
        <div className="max-w-sm p-8 text-[var(--color-text-muted)]">
          <p className="font-display text-2xl text-[var(--color-text)]">
            Mapbox token missing
          </p>
          <p className="mt-2 text-sm">
            Add <code>NEXT_PUBLIC_MAPBOX_TOKEN</code> to <code>frontend/.env.local</code>.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-[560px] items-center justify-center bg-[var(--color-surface)] text-center">
        <div className="max-w-sm p-8">
          <p className="font-display text-2xl text-[var(--color-rose)]">
            Map data unavailable
          </p>
          <p className="mt-2 text-sm text-[var(--color-text-muted)]">
            {error}. Is the backend running?
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-[560px] w-full">
      <Map
        ref={mapRef}
        mapboxAccessToken={MAPBOX_TOKEN}
        initialViewState={{
          longitude: -66.45,
          latitude: 18.22,
          zoom: 8.5,
        }}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        interactiveLayerIds={interactiveLayers}
        onClick={handleMapClick}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        cursor={viewState === "island" ? "pointer" : "default"}
      >
        {muniGeojson && (
          <Source
            id="munis"
            type="geojson"
            data={muniGeojson}
            promoteId="id"
          >
            <Layer {...muniFillLayer} />
            <Layer {...muniLineLayer} />
            <Layer {...muniHighlightLineLayer} />
          </Source>
        )}

        {barrioGeojson && viewState === "muni" && (
          <Source
            id="barrios"
            type="geojson"
            data={barrioGeojson}
            promoteId="id"
          >
            <Layer {...barrioFillLayer} />
            <Layer {...barrioLineLayer} />
            <Layer {...barrioHighlightLineLayer} />
          </Source>
        )}
      </Map>

      {/* Loading overlay for barrios */}
      {viewState === "muni" && !barrioGeojson && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-[var(--color-ink)]/30 backdrop-blur-[2px]">
          <div className="font-mono text-xs uppercase tracking-widest text-[var(--color-teal-soft)]">
            Cargando barrios…
          </div>
        </div>
      )}

      {/* Tooltip */}
      {hoverInfo && (
        <div
          className="pointer-events-none absolute z-10 max-w-xs border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-3 py-2 text-sm shadow-2xl"
          style={{
            left: hoverInfo.x + 12,
            top: hoverInfo.y + 12,
          }}
        >
          <div className="font-display text-base leading-tight text-[var(--color-text)]">
            {hoverInfo.name}
          </div>
          {hoverInfo.value !== null && meta ? (
            <div
              className={`mt-1 font-display text-xl leading-none ${
                hoverInfo.reliable
                  ? "text-[var(--color-amber)]"
                  : "text-[var(--color-text-muted)]"
              }`}
            >
              {formatValue(hoverInfo.value, meta.unit)}
              {!hoverInfo.reliable && (
                <span className="ml-2 font-mono text-[10px] uppercase tracking-wider text-[var(--color-amber-soft)]">
                  alta variabilidad
                </span>
              )}
            </div>
          ) : (
            <div className="mt-1 text-xs italic text-[var(--color-text-muted)]">
              sin datos
            </div>
          )}
          <div className="mt-1.5 font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-subtle)]">
            {hoverSource === "barrios" ? "BARRIO" : "FIPS"} {hoverInfo.id}
            {hoverInfo.population != null && (
              <> · {hoverInfo.population.toLocaleString("es-PR")} hab.</>
            )}
          </div>
        </div>
      )}

      {/* Island view: loading */}
      {!muniGeojson && !error && viewState === "island" && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-[var(--color-ink)]/40 backdrop-blur-sm">
          <div className="font-mono text-xs uppercase tracking-widest text-[var(--color-teal-soft)]">
            Cargando datos…
          </div>
        </div>
      )}

      {/* Click-to-drill hint (island view only, first render) */}
      {viewState === "island" && muniGeojson && (
        <div className="pointer-events-none absolute bottom-4 left-4 border border-[var(--color-border)] bg-[var(--color-surface-elevated)]/90 px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest text-[var(--color-text-muted)] backdrop-blur-sm">
          Clic en un municipio para ver sus barrios
        </div>
      )}
    </div>
  );
}
