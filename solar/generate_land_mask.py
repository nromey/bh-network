#!/usr/bin/env python3
"""
Generate a MUF resolution mask from a Natural Earth land shapefile.

Depends on the `pyshp` library (`pip install pyshp`).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

try:
    import shapefile  # type: ignore
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: pyshp. Install with 'python3 -m pip install --user pyshp'."
    ) from exc


Point = Tuple[float, float]


@dataclass(frozen=True)
class Ring:
    points: List[Point]
    is_hole: bool


@dataclass(frozen=True)
class ShapeInfo:
    bbox: Tuple[float, float, float, float]
    rings: List[Ring]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate land-aware MUF mask from Natural Earth shapefile"
    )
    parser.add_argument("shapefile", type=Path, help="Path to Natural Earth land .shp")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("solar", "land_mask_generated.json"),
        help="Destination mask JSON (default: solar/land_mask_generated.json)",
    )
    parser.add_argument(
        "--default-step",
        type=float,
        default=5.0,
        help="Fallback sampling step in degrees for non-land tiles (default: %(default)s)",
    )
    parser.add_argument(
        "--land-step",
        type=float,
        default=1.0,
        help="Sampling step to apply on land tiles (default: %(default)s)",
    )
    parser.add_argument(
        "--lat-min",
        type=int,
        default=-90,
        help="Minimum latitude to evaluate (default: %(default)s)",
    )
    parser.add_argument(
        "--lat-max",
        type=int,
        default=90,
        help="Maximum latitude to evaluate (exclusive upper bound, default: %(default)s)",
    )
    parser.add_argument(
        "--lon-min",
        type=int,
        default=-180,
        help="Minimum longitude to evaluate (default: %(default)s)",
    )
    parser.add_argument(
        "--lon-max",
        type=int,
        default=180,
        help="Maximum longitude to evaluate (exclusive upper bound, default: %(default)s)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress while marching through the grid",
    )
    return parser.parse_args()


def load_shapes(path: Path) -> List[ShapeInfo]:
    reader = shapefile.Reader(str(path))
    shapes: List[ShapeInfo] = []
    for shape in reader.shapes():
        bbox = tuple(shape.bbox)  # type: ignore[assignment]
        points = shape.points
        parts = list(shape.parts) + [len(points)]
        rings: List[Ring] = []
        for i in range(len(parts) - 1):
            start, end = parts[i], parts[i + 1]
            ring_points = points[start:end]
            if not ring_points:
                continue
            if ring_points[0] != ring_points[-1]:
                ring_points = ring_points + [ring_points[0]]
            area = polygon_area(ring_points)
            is_hole = area > 0  # Natural Earth uses clockwise (<0) for outer rings
            rings.append(Ring(points=ring_points, is_hole=is_hole))
        shapes.append(ShapeInfo(bbox=bbox, rings=rings))
    return shapes


def polygon_area(points: List[Point]) -> float:
    area = 0.0
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def point_in_shape(lon: float, lat: float, shape: ShapeInfo) -> bool:
    minx, miny, maxx, maxy = shape.bbox
    if lon < minx or lon > maxx or lat < miny or lat > maxy:
        return False
    inside = False
    for ring in shape.rings:
        if point_in_ring(lon, lat, ring.points):
            if ring.is_hole:
                inside = False
                continue
            inside = True
    return inside


def point_in_ring(lon: float, lat: float, ring: List[Point]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        intersects = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def scan_land_cells(
    shapes: List[ShapeInfo],
    lat_min: int,
    lat_max: int,
    lon_min: int,
    lon_max: int,
    verbose: bool = False,
) -> List[Tuple[int, int]]:
    land_cells: List[Tuple[int, int]] = []
    total_rows = lat_max - lat_min
    for idx, lat in enumerate(range(lat_min, lat_max)):
        lat_center = lat + 0.5
        if verbose:
            percent = 100.0 * idx / total_rows
            print(f"Scanning latitude {lat:+3d}° ({percent:5.1f}%)")
        for lon in range(lon_min, lon_max):
            lon_center = lon + 0.5
            if any(point_in_shape(lon_center, lat_center, shape) for shape in shapes):
                land_cells.append((lat, lon))
    return land_cells


def build_mask(
    land_cells: Iterable[Tuple[int, int]],
    default_step: float,
    land_step: float,
) -> dict:
    regions = []
    for lat, lon in land_cells:
        regions.append(
            {
                "name": f"land_cell_{lat:+03d}_{lon:+04d}",
                "lat_min": float(lat),
                "lat_max": float(lat),
                "lon_min": float(lon),
                "lon_max": float(lon),
                "step": land_step,
            }
        )
    regions.sort(key=lambda entry: (entry["lat_min"], entry["lon_min"]))
    return {"default_step": default_step, "regions": regions}


def write_mask(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def main() -> int:
    args = parse_args()
    shapes = load_shapes(args.shapefile)
    if args.verbose:
        print(f"Loaded {len(shapes)} shapes from {args.shapefile}")
    land_cells = scan_land_cells(
        shapes=shapes,
        lat_min=args.lat_min,
        lat_max=args.lat_max,
        lon_min=args.lon_min,
        lon_max=args.lon_max,
        verbose=args.verbose,
    )
    if args.verbose:
        print(f"Identified {len(land_cells)} land cells at {args.land_step}° resolution")
    mask = build_mask(
        land_cells=land_cells,
        default_step=args.default_step,
        land_step=args.land_step,
    )
    write_mask(args.output, mask)
    if args.verbose:
        print(f"Wrote mask to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
