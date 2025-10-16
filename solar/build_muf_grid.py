#!/usr/bin/env python3
"""
Wrapper script for the IRI MUF driver that materializes a global MUF grid JSON.

The driver executable (`solar/iri_muf_driver`) emits MUF values for a single
latitude/longitude at a specified UTC timestamp. This script fans out across a
coarse grid (default 2°) and assembles the results into the canonical
`solar_muf_grid.json` structure described in `solar_agents.md`.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import subprocess
import sys
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Dict, List, Sequence

from mask_utils import build_coordinate_map, load_mask, steps_summary


@dataclass(frozen=True)
class GridSpec:
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    step_deg: float


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate solar MUF grid JSON via the IRI MUF driver"
    )
    parser.add_argument(
        "--driver",
        type=Path,
        default=Path(__file__).resolve().parent / "iri_muf_driver",
        help="Path to the compiled iri_muf_driver executable (default: %(default)s)",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=2.0,
        help="Grid resolution in degrees (default: %(default)s)",
    )
    parser.add_argument(
        "--lat-min",
        type=float,
        default=-90.0,
        help="Minimum latitude (default: %(default)s)",
    )
    parser.add_argument(
        "--lat-max",
        type=float,
        default=90.0,
        help="Maximum latitude (default: %(default)s)",
    )
    parser.add_argument(
        "--lon-min",
        type=float,
        default=-180.0,
        help="Minimum longitude (default: %(default)s)",
    )
    parser.add_argument(
        "--lon-max",
        type=float,
        default=180.0,
        help="Maximum longitude (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "solar_muf_grid.json",
        help="Destination file for the grid JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--mask",
        type=Path,
        default=None,
        help="Optional JSON mask describing regional sampling steps",
    )
    parser.add_argument(
        "--driver-cwd",
        type=Path,
        default=None,
        help=(
            "Working directory for the driver (defaults to alongside the Fortran data files). "
            "Only needed if running with a custom layout."
        ),
    )
    parser.add_argument(
        "--timestamp",
        type=str,
        default=None,
        help="UTC timestamp in ISO-8601 (default: now)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress logging to stderr",
    )
    parser.add_argument(
        "--workers",
        type=str,
        default="1",
        help="Number of parallel workers (integer or 'auto'; default: %(default)s)",
    )
    return parser.parse_args(argv)


def resolve_timestamp(timestamp_arg: str | None) -> dt.datetime:
    if not timestamp_arg:
        return dt.datetime.now(dt.timezone.utc)
    normalized = timestamp_arg.strip()
    if normalized.lower() == "now":
        return dt.datetime.now(dt.timezone.utc)
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    ts = dt.datetime.fromisoformat(normalized)
    if ts.tzinfo is None:
        raise ValueError("Timestamp must include timezone information or Z suffix")
    return ts.astimezone(dt.timezone.utc)


def resolve_workers(arg: str) -> int:
    value = arg.strip().lower()
    if value == "auto":
        cpu_total = os.cpu_count() or 1
        return max(1, cpu_total - 1) if cpu_total > 1 else 1
    try:
        workers = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid workers value '{arg}'") from exc
    if workers <= 0:
        raise ValueError("workers must be a positive integer")
    return workers


def timestamp_fields_from_dt(when_utc: dt.datetime) -> tuple[int, int, int, float]:
    decimal_hours = (
        when_utc.hour
        + when_utc.minute / 60.0
        + when_utc.second / 3600.0
        + when_utc.microsecond / 3_600_000_000.0
    )
    return (when_utc.year, when_utc.month, when_utc.day, decimal_hours)


def run_driver(
    driver_path: Path,
    driver_cwd: Path,
    timestamp_fields: tuple[int, int, int, float],
    lat: float,
    lon: float,
) -> dict:
    year, month, day, decimal_hours = timestamp_fields
    args: List[str] = [
        str(driver_path),
        str(year),
        str(month),
        str(day),
        f"{decimal_hours:.6f}",
        f"{lat:.6f}",
        f"{lon:.6f}",
    ]
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        cwd=str(driver_cwd) if driver_cwd else None,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Driver failed for lat={lat}, lon={lon} with code {result.returncode}: {result.stderr.strip()}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Failed to parse driver JSON for lat={lat}, lon={lon}: {exc}\nOutput was:\n{result.stdout}"
        ) from exc


def build_tiles(
    driver_path: Path,
    driver_cwd: Path,
    timestamp_fields: tuple[int, int, int, float],
    lat_to_lons: Dict[float, List[float]],
    workers: int,
    quiet: bool,
) -> List[dict]:
    lat_values = list(lat_to_lons.keys())
    total = sum(len(lat_to_lons[lat]) for lat in lat_values)
    tiles: List[dict] = []
    completed = 0

    if workers == 1:
        driver_cwd_str = str(driver_cwd) if driver_cwd else ""
        for lat in lat_values:
            lon_values = lat_to_lons[lat]
            row_tiles = _compute_row(
                str(driver_path),
                driver_cwd_str,
                timestamp_fields,
                lat,
                lon_values,
            )
            tiles.extend(row_tiles)
            completed += len(lon_values)
            if not quiet:
                print(
                    f"Computed lat {lat:+06.2f}° ({completed}/{total} tiles)",
                    file=sys.stderr,
                )
    else:
        driver_cwd_str = str(driver_cwd) if driver_cwd else ""
        try:
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
                row_iter = pool.map(
                    _compute_row,
                    [str(driver_path)] * len(lat_values),
                    [driver_cwd_str] * len(lat_values),
                    [timestamp_fields] * len(lat_values),
                    lat_values,
                    [lat_to_lons[lat] for lat in lat_values],
                )
                for lat, row_tiles in zip(lat_values, row_iter):
                    tiles.extend(row_tiles)
                    completed += len(lat_to_lons[lat])
                    if not quiet:
                        print(
                            f"[{workers} workers] Computed lat {lat:+06.2f}° "
                            f"({completed}/{total} tiles)",
                            file=sys.stderr,
                        )
        except PermissionError as exc:
            if not quiet:
                print(
                    f"Parallel execution unavailable ({exc}); falling back to single worker.",
                    file=sys.stderr,
                )
            return build_tiles(
                driver_path=driver_path,
                driver_cwd=driver_cwd,
                timestamp_fields=timestamp_fields,
                lat_to_lons=lat_to_lons,
                workers=1,
                quiet=quiet,
            )
    return tiles


def _compute_row(
    driver_path: str,
    driver_cwd: str,
    timestamp_fields: tuple[int, int, int, float],
    lat: float,
    lon_values: Sequence[float],
) -> List[dict]:
    path_obj = Path(driver_path)
    cwd_obj = Path(driver_cwd) if driver_cwd else None
    row: List[dict] = []
    for lon in lon_values:
        payload = run_driver(path_obj, cwd_obj, timestamp_fields, lat, lon)
        muf = payload.get("muf", {})
        row.append(
            {
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "muf": {
                    "nvis": muf.get("nvis", {}).get("muf_mhz"),
                    "regional": muf.get("regional", {}).get("muf_mhz"),
                    "dx": muf.get("dx_secant", {}).get("muf_mhz"),
                },
            }
        )
    return row


def write_json(output_path: Path, payload: dict) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")
    temp_path.replace(output_path)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    driver_path: Path = args.driver
    if not driver_path.exists():
        print(f"Driver executable not found at {driver_path}", file=sys.stderr)
        return 2
    driver_cwd: Path
    if args.driver_cwd:
        driver_cwd = args.driver_cwd
    else:
        candidate = driver_path.parent / "iri_driver"
        driver_cwd = candidate if candidate.exists() else driver_path.parent
    try:
        workers = resolve_workers(args.workers)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    when_utc = resolve_timestamp(args.timestamp)
    timestamp_fields = timestamp_fields_from_dt(when_utc)
    grid = GridSpec(
        lat_min=args.lat_min,
        lat_max=args.lat_max,
        lon_min=args.lon_min,
        lon_max=args.lon_max,
        step_deg=args.step,
    )
    mask_config = None
    if args.mask:
        try:
            mask_config = load_mask(args.mask)
        except Exception as exc:
            print(f"Failed to load mask {args.mask}: {exc}", file=sys.stderr)
            return 2
    lat_to_lons = build_coordinate_map(
        lat_min=grid.lat_min,
        lat_max=grid.lat_max,
        lon_min=grid.lon_min,
        lon_max=grid.lon_max,
        fallback_step=grid.step_deg,
        mask=mask_config,
    )
    step_options = steps_summary(mask_config, grid.step_deg)
    if not args.quiet:
        message = (
            f"Building MUF grid at {when_utc.isoformat()} "
            f"(lat={grid.lat_min}..{grid.lat_max}, "
            f"lon={grid.lon_min}..{grid.lon_max}, workers={workers}, "
            f"steps={step_options})"
        )
        if mask_config:
            message += f" using mask {args.mask.name}"
        print(message, file=sys.stderr)
    tiles = build_tiles(
        driver_path,
        driver_cwd,
        timestamp_fields,
        lat_to_lons,
        workers=workers,
        quiet=args.quiet,
    )
    payload = {
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cell_deg": grid.step_deg,
        "source_timestamp": when_utc.isoformat(),
        "tiles": tiles,
    }
    payload["steps_deg"] = step_options
    if mask_config:
        payload["mask_summary"] = {
            "default_step": mask_config.default_step,
            "region_count": len(mask_config.regions),
        }
    write_json(args.output, payload)
    if not args.quiet:
        print(f"Wrote {len(tiles)} tiles to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
