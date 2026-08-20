import { useEffect, useMemo } from "react";
import L from "leaflet";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import type { GeoJsonFeatureCollection } from "../lib/types";
import { computeBounds } from "../lib/geo";

type Props = {
  hospitals?: GeoJsonFeatureCollection | null;
  roads?: GeoJsonFeatureCollection | null;
  rivers?: GeoJsonFeatureCollection | null;
  population?: GeoJsonFeatureCollection | null;
  boundaries?: GeoJsonFeatureCollection | null;
  analysis?: GeoJsonFeatureCollection | null;
  recommendations?: GeoJsonFeatureCollection | null;
  showLayers: Record<string, boolean>;
  focusCollection?: GeoJsonFeatureCollection | null;
  loading?: boolean;
};

function FitToData({ collections }: { collections: Array<GeoJsonFeatureCollection | null | undefined> }) {
  const map = useMap();
  const bounds = useMemo(() => computeBounds(collections), [collections]);

  useEffect(() => {
    if (bounds) {
      map.fitBounds(bounds, { padding: [24, 24] });
    }
  }, [bounds, map]);

  return null;
}

export function GeoMap({
  hospitals,
  roads,
  rivers,
  population,
  boundaries,
  analysis,
  recommendations,
  showLayers,
  focusCollection,
  loading,
}: Props) {
  const visibleCollections = useMemo(
    () => [
      showLayers.hospitals ? hospitals : null,
      showLayers.roads ? roads : null,
      showLayers.rivers ? rivers : null,
      showLayers.population ? population : null,
      showLayers.boundaries ? boundaries : null,
      analysis,
      recommendations,
    ],
    [analysis, boundaries, hospitals, population, recommendations, rivers, roads, showLayers.boundaries, showLayers.hospitals, showLayers.population, showLayers.rivers, showLayers.roads],
  );

  return (
    <div className="relative h-[620px] overflow-hidden rounded-3xl border border-white/10 bg-slate-950 shadow-glow">
      <MapContainer center={[18.52, 73.86]} zoom={12} className="h-full w-full">
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitToData collections={visibleCollections} />

        {showLayers.boundaries && boundaries && (
          <GeoJSON
            data={boundaries as any}
            style={{
              color: "#7dd3fc",
              weight: 2,
              fillColor: "#0f172a",
              fillOpacity: 0.12,
            }}
          />
        )}

        {showLayers.population && population && (
          <GeoJSON
            data={population as any}
            style={(feature) => ({
              color: "#f59e0b",
              weight: 1,
              fillColor: "#fbbf24",
              fillOpacity: feature?.properties?.density ? Math.min(Number(feature.properties.density) / 20000, 0.7) : 0.25,
            })}
          />
        )}

        {showLayers.roads && roads && (
          <GeoJSON
            data={roads as any}
            style={(feature) => ({
              color: feature?.properties?.road_type === "major" ? "#fb923c" : "#94a3b8",
              weight: feature?.properties?.road_type === "major" ? 4 : 2,
            })}
          />
        )}

        {showLayers.rivers && rivers && (
          <GeoJSON
            data={rivers as any}
            style={{
              color: "#38bdf8",
              weight: 3,
            }}
          />
        )}

        {showLayers.hospitals && hospitals && (
          <GeoJSON
            data={hospitals as any}
            pointToLayer={(_feature, latlng) =>
              L.circleMarker(latlng, { radius: 8, color: "#e2e8f0", weight: 1, fillColor: "#22c55e", fillOpacity: 0.95 })
            }
            onEachFeature={(feature, layer) => {
              const props = feature.properties as Record<string, unknown>;
              layer.bindPopup(
                `<strong>${String(props.name ?? "Hospital")}</strong><br/>${String(props.type ?? "facility")}<br/>${String(props.address ?? "")}`
              );
            }}
          />
        )}

        {analysis && (
          <GeoJSON
            data={analysis as any}
            style={{
              color: "#facc15",
              weight: 3,
              fillColor: "#facc15",
              fillOpacity: 0.2,
            }}
            pointToLayer={(_feature, latlng) => L.circleMarker(latlng, { radius: 10, color: "#facc15", weight: 2, fillColor: "#fde047", fillOpacity: 0.9 })}
            onEachFeature={(feature, layer) => {
              const props = feature.properties as Record<string, unknown>;
              layer.bindPopup(
                `<strong>${String(props.name ?? "Analysis result")}</strong><br/>Score: ${String(props.score ?? "n/a")}<br/>${String(props.reason ?? "")}`
              );
            }}
          />
        )}

        {recommendations && (
          <GeoJSON
            data={recommendations as any}
            pointToLayer={(_feature, latlng) =>
              L.circleMarker(latlng, { radius: 11, color: "#f8fafc", weight: 2, fillColor: "#f97316", fillOpacity: 0.95 })
            }
            onEachFeature={(feature, layer) => {
              const props = feature.properties as Record<string, unknown>;
              layer.bindPopup(
                `<strong>${String(props.name ?? "Recommended site")}</strong><br/>Score: ${String(props.score ?? "n/a")}<br/>${String(props.reason ?? "")}`
              );
            }}
          />
        )}

        {focusCollection && <FitToData collections={[focusCollection]} />}
      </MapContainer>

      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-950/35 backdrop-blur-[1px]">
          <div className="rounded-2xl border border-white/15 bg-slate-950/90 px-5 py-3 text-sm text-slate-100 shadow-glow">
            Running spatial analysis and loading geospatial layers...
          </div>
        </div>
      )}

      <div className="pointer-events-none absolute left-4 top-4 rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-xs text-slate-200 backdrop-blur">
        <div className="font-semibold uppercase tracking-[0.2em] text-geo-300">GeoAI Map</div>
        <div className="mt-1 text-slate-400">OpenStreetMap + WorldPop + live spatial analysis</div>
      </div>
    </div>
  );
}
