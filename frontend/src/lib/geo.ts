import type { GeoJsonFeatureCollection } from "./types";

export function computeBounds(collections: Array<GeoJsonFeatureCollection | null | undefined>): [[number, number], [number, number]] | null {
  let minLat = Number.POSITIVE_INFINITY;
  let minLng = Number.POSITIVE_INFINITY;
  let maxLat = Number.NEGATIVE_INFINITY;
  let maxLng = Number.NEGATIVE_INFINITY;

  const visit = (coords: unknown): void => {
    if (!Array.isArray(coords)) return;
    if (coords.length >= 2 && typeof coords[0] === "number" && typeof coords[1] === "number") {
      const [lng, lat] = coords as [number, number];
      minLat = Math.min(minLat, lat);
      minLng = Math.min(minLng, lng);
      maxLat = Math.max(maxLat, lat);
      maxLng = Math.max(maxLng, lng);
      return;
    }
    coords.forEach(visit);
  };

  collections.forEach((collection) => {
    if (!collection) return;
    collection.features.forEach((feature) => {
      visit((feature.geometry as GeoJSON.Geometry & { coordinates?: unknown }).coordinates);
    });
  });

  if (!Number.isFinite(minLat)) return null;
  return [
    [minLat, minLng],
    [maxLat, maxLng],
  ] as [[number, number], [number, number]];
}

export function formatScore(value?: unknown) {
  if (typeof value !== "number") return "n/a";
  return `${Math.round(value)}`;
}
