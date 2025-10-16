#!/usr/bin/env python3
"""
Helper CLI to inspect MUF grid mask resolution at a given coordinate.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mask_utils import apply_mask_step, load_mask, regions_for_point


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query mask sampling step at a coordinate")
    parser.add_argument("mask", type=Path, help="Path to mask JSON file")
    parser.add_argument("--lat", type=float, required=True, help="Latitude in degrees")
    parser.add_argument("--lon", type=float, required=True, help="Longitude in degrees")
    parser.add_argument(
        "--fallback-step",
        type=float,
        default=2.0,
        help="Fallback step when no mask regions apply (default: %(default)s)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        mask = load_mask(args.mask)
    except Exception as exc:
        print(f"Failed to load mask: {exc}")
        return 2
    step = apply_mask_step(mask, args.lat, args.lon, args.fallback_step)
    hits = regions_for_point(mask, args.lat, args.lon)
    region_text = ", ".join(hits) if hits else "none"
    print(f"lat={args.lat:+.2f}°, lon={args.lon:+.2f}° -> step {step:.2f}° (regions: {region_text})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
