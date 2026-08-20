from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import Polygon, box, mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import settings


def _study_area_geometry(bbox_text: str, boundary_path: Path | None = None) -> Polygon:
    if boundary_path and boundary_path.exists():
        payload = json.loads(boundary_path.read_text(encoding="utf-8"))
        features = payload.get("features", [])
        if features:
            return Polygon(features[0]["geometry"]["coordinates"][0])
    parts = [float(part.strip()) for part in bbox_text.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must contain exactly four comma-separated numbers")
    return box(*parts)


def _polygon_for_cell(transform, row: int, col: int) -> Polygon:
    x0, y1 = transform * (col, row)
    x1, y0 = transform * (col + 1, row + 1)
    return box(x0, y0, x1, y1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clip the WorldPop raster to Pune and derive analysis-ready outputs.")
    parser.add_argument("--source", default=str(settings.worldpop_tif_path), help="Path to the WorldPop GeoTIFF")
    parser.add_argument("--bbox", default=settings.study_area_bbox, help="Study-area bounding box minLon,minLat,maxLon,maxLat")
    parser.add_argument("--boundary", default=settings.study_area_boundary_geojson, help="Optional Pune boundary GeoJSON")
    parser.add_argument("--output-dir", default=str(settings.real_data_dir), help="Directory for clipped raster and derived outputs")
    args = parser.parse_args()

    source_path = Path(args.source).expanduser().resolve()
    if not source_path.exists():
        raise SystemExit(f"WorldPop source file not found: {source_path}")

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    boundary_path = Path(args.boundary).expanduser().resolve() if args.boundary.strip() else None
    study_area = _study_area_geometry(args.bbox, boundary_path)

    crs_text = ""
    nodata_value: float | int | None = None
    resolution = (0.0, 0.0)
    clip_path = output_dir / "worldpop_pune_clip.tif"

    with rasterio.open(source_path) as src:
        crs_text = str(src.crs)
        nodata_value = src.nodata
        resolution = (abs(src.res[0]), abs(src.res[1]))
        clipped, clipped_transform = mask(src, [mapping(study_area)], crop=True, filled=True, nodata=src.nodata)
        profile = src.profile.copy()
        profile.update(
            {
                "height": clipped.shape[1],
                "width": clipped.shape[2],
                "transform": clipped_transform,
            }
        )

        with rasterio.open(clip_path, "w", **profile) as dst:
            dst.write(clipped)

        band = clipped[0]
        valid_mask = np.isfinite(band)
        if src.nodata is not None:
            valid_mask &= band != src.nodata
        valid_mask &= band >= 0

        valid_values = band[valid_mask].astype(float)
        valid_indices = np.argwhere(valid_mask)
        pixel_width = abs(clipped_transform.a)
        pixel_height = abs(clipped_transform.e)
        cell_area_sqkm = (pixel_width * pixel_height) * 12321.0  # approx. square degrees to square km near Pune

        features: list[dict[str, Any]] = []
        for row, col in valid_indices:
            value = float(band[row, col])
            if value < 0:
                continue
            polygon = _polygon_for_cell(clipped_transform, int(row), int(col))
            features.append(
                {
                    "type": "Feature",
                    "id": f"cell-{row}-{col}",
                    "properties": {
                        "population": round(value, 3),
                        "density": round(value / max(cell_area_sqkm, 1e-9), 3),
                        "cell_area_sqkm": round(cell_area_sqkm, 6),
                        "row": int(row),
                        "col": int(col),
                        "source": "WorldPop",
                    },
                    "geometry": mapping(polygon),
                }
            )

    stats = {
        "source_path": str(source_path),
        "clip_path": str(clip_path),
        "crs": crs_text,
        "bounds": [float(v) for v in study_area.bounds],
        "resolution": [resolution[0], resolution[1]],
        "nodata": nodata_value,
        "band_count": int(clipped.shape[0]),
        "valid_cell_count": int(valid_values.size),
        "total_population": round(float(valid_values.sum()), 3),
        "mean_population": round(float(valid_values.mean()), 3) if valid_values.size else 0.0,
        "min_population": round(float(valid_values.min()), 3) if valid_values.size else 0.0,
        "max_population": round(float(valid_values.max()), 3) if valid_values.size else 0.0,
        "cell_area_sqkm": round(cell_area_sqkm, 6),
        "study_area": settings.study_area_name,
        "clip_bbox": [float(v) for v in args.bbox.split(",")],
    }

    population_geojson = {
        "type": "FeatureCollection",
        "name": "population",
        "features": features,
    }

    (output_dir / "population.geojson").write_text(json.dumps(population_geojson, indent=2), encoding="utf-8")
    (output_dir / "worldpop_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
