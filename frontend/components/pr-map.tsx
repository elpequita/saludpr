"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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

type GeoFeature = GeoJSON.Feature<
  GeoJSON.Geometry,
  {
    id: string;
    name: string;
    area_sq_km: number | null;
    population_latest: number | null;
    value: number | null;
    value_type: string | null;
    year: number | null;
    is_suppressed: boolean | null;
    is_estimated: boolean | null;
  }
>;

type HoverInfo = {
  name: string;
  id: string;
  area: number | null;
  value: number | null;
  valueType: string | null;
  x: number;
  y: number;
};

type Props = {
  indicator: string;
  year: number;
  onBreaksComputed?: (breaks: number[]) => void;
};

export function PRMap({ indicator, year, onBreaksComputed }: Props) {
  const mapRef = useRef<MapRef>(null);
  const [geojson, setGeojson] = useState<GeoJSON.FeatureCollection | null>(
    null,
  );
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  const meta = INDICATORS[indicator];

  // Fetch the enriched GeoJSON whenever indicator/year changes
  useEffect(() => {
    let cancelled = false;
    setGeojson(null);

    const url = new URL("/api/municipalities", window.location.origin);
    url.searchParams.set("indicator", indicator);
    url.searchParams.set("year", String(year));

    fetch(url.toString())
      .then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json() as Promise<GeoJSON.FeatureCollection>;
      })
      .then((data) => {
        if (!cancelled) setGeojson(data);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load map data");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [indicator, year]);

  // Compute quintile breaks for the current indicator
  const breaks = useMemo<number[] | null>(() => {
    if (!geojson) return null;
    const values = (geojson.features as GeoFeature[])
      .map((f) => f.properties.value)
      .filter((v): v is number => v !== null && v !== undefined);
    if (values.length === 0) return null;
    return quintileBreaks(values);
  }, [geojson]);

  // Notify parent of breaks for shared legend
  useEffect(() => {
    if (breaks) onBreaksComputed?.(breaks);
  }, [breaks, onBreaksComputed]);

  // Mapbox choropleth color expression — built from breaks + direction
  const fillLayer: LayerProps = useMemo(() => {
    const ramp = COLOR_RAMPS[meta?.direction ?? "neutral"];
    const noData = "#0e1d24";

    const colorExpression: mapboxgl.FillPaint["fill-color"] = breaks
      ? [
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
          ]
        ]
      : noData;

    return {
      id: "municipalities-fill",
      type: "fill",
      paint: {
        "fill-color": colorExpression,
        "fill-opacity": [
          "case",
          ["boolean", ["feature-state", "hover"], false],
          0.95,
          0.78,
        ],
      },
    };
  }, [breaks, meta]);

  const lineLayer: LayerProps = {
    id: "municipalities-line",
    type: "line",
    paint: {
      "line-color": "#0a1519",
      "line-width": 0.4,
      "line-opacity": 0.6,
    },
  };

  const highlightLineLayer: LayerProps = {
    id: "municipalities-line-highlight",
    type: "line",
    paint: {
      "line-color": "#f59e0b",
      "line-width": [
        "case",
        ["boolean", ["feature-state", "hover"], false],
        2.5,
        0,
      ],
    },
  };

  if (!MAPBOX_TOKEN) {
    return (
      <div className="flex h-[560px] items-center justify-center bg-[var(--color-surface)] text-center">
        <div className="max-w-sm p-8 text-[var(--color-text-muted)]">
          <p className="font-display text-2xl text-[var(--color-text)]">
            Mapbox token missing
          </p>
          <p className="mt-2 text-sm">
            Add NEXT_PUBLIC_MAPBOX_TOKEN to frontend/.env.local.
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
        interactiveLayerIds={["municipalities-fill"]}
        onMouseMove={(e) => {
          const feat = e.features?.[0] as GeoFeature | undefined;
          if (!feat) {
            if (hoverId !== null) {
              mapRef.current?.setFeatureState(
                { source: "municipalities", id: hoverId },
                { hover: false },
              );
            }
            setHoverId(null);
            setHoverInfo(null);
            return;
          }
          const id = String(feat.properties.id);
          if (id !== hoverId) {
            if (hoverId !== null) {
              mapRef.current?.setFeatureState(
                { source: "municipalities", id: hoverId },
                { hover: false },
              );
            }
            mapRef.current?.setFeatureState(
              { source: "municipalities", id },
              { hover: true },
            );
            setHoverId(id);
          }
          setHoverInfo({
            id,
            name: feat.properties.name,
            area: feat.properties.area_sq_km,
            value: feat.properties.value,
            valueType: feat.properties.value_type,
            x: e.point.x,
            y: e.point.y,
          });
        }}
        onMouseLeave={() => {
          if (hoverId !== null) {
            mapRef.current?.setFeatureState(
              { source: "municipalities", id: hoverId },
              { hover: false },
            );
          }
          setHoverId(null);
          setHoverInfo(null);
        }}
      >
        {geojson && (
          <Source
            id="municipalities"
            type="geojson"
            data={geojson}
            promoteId="id"
          >
            <Layer {...fillLayer} />
            <Layer {...lineLayer} />
            <Layer {...highlightLineLayer} />
          </Source>
        )}
      </Map>

      {/* Tooltip */}
      {hoverInfo && (
        <div
          className="pointer-events-none absolute z-10 border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-3 py-2 text-sm shadow-2xl"
          style={{
            left: hoverInfo.x + 12,
            top: hoverInfo.y + 12,
          }}
        >
          <div className="font-display text-base leading-tight text-[var(--color-text)]">
            {hoverInfo.name}
          </div>
          {hoverInfo.value !== null && meta ? (
            <div className="mt-1 font-display text-xl leading-none text-[var(--color-amber)]">
              {formatValue(hoverInfo.value, meta.unit)}
            </div>
          ) : (
            <div className="mt-1 text-xs italic text-[var(--color-text-muted)]">
              sin datos
            </div>
          )}
          <div className="mt-1.5 font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-subtle)]">
            FIPS {hoverInfo.id}
            {hoverInfo.area !== null && <> · {hoverInfo.area.toFixed(1)} km²</>}
          </div>
        </div>
      )}

      {/* Loading overlay */}
      {!geojson && !error && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-[var(--color-ink)]/40 backdrop-blur-sm">
          <div className="font-mono text-xs uppercase tracking-widest text-[var(--color-teal-soft)]">
            Cargando datos…
          </div>
        </div>
      )}
    </div>
  );
}
