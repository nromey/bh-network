"""
Utilities for MUF grid resolution masks.

The mask describes geographic regions and the preferred sampling step (in
degrees) for each region. Regions are axis-aligned latitude/longitude boxes.
The configuration is intentionally simple so it can be authored and reviewed in
plain text without visual tooling.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class MaskRegion:
    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    step: float


@dataclass(frozen=True)
class MaskConfig:
    default_step: float
    regions: List[MaskRegion]

    @property
    def steps(self) -> List[float]:
        values = {self.default_step}
        for region in self.regions:
            values.add(region.step)
        return sorted(values)


def _inclusive_range(start: float, stop: float, step: float) -> Iterable[float]:
    if step <= 0:
        raise ValueError("step must be positive")
    current = start
    epsilon = 1e-9
    while current <= stop + epsilon:
        yield round(current, 6)
        current += step


def load_mask(path: Path) -> MaskConfig:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    try:
        default_step = float(data["default_step"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Mask file must define numeric 'default_step'") from exc
    regions_raw = data.get("regions", [])
    regions: List[MaskRegion] = []
    for index, entry in enumerate(regions_raw):
        try:
            region = MaskRegion(
                name=str(entry["name"]),
                lat_min=float(entry["lat_min"]),
                lat_max=float(entry["lat_max"]),
                lon_min=float(entry["lon_min"]),
                lon_max=float(entry["lon_max"]),
                step=float(entry["step"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid region at index {index}: {entry}") from exc
        regions.append(region)
    return MaskConfig(default_step=default_step, regions=regions)


def apply_mask_step(
    mask: MaskConfig | None, lat: float, lon: float, fallback_step: float
) -> float:
    step = fallback_step
    if mask:
        step = mask.default_step
        for region in mask.regions:
            if (
                region.lat_min <= lat <= region.lat_max
                and region.lon_min <= lon <= region.lon_max
            ):
                step = min(step, region.step)
    return step


def regions_for_point(mask: MaskConfig | None, lat: float, lon: float) -> List[str]:
    if not mask:
        return []
    hits: List[str] = []
    for region in mask.regions:
        if (
            region.lat_min <= lat <= region.lat_max
            and region.lon_min <= lon <= region.lon_max
        ):
            hits.append(region.name)
    return hits


def build_coordinate_map(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    fallback_step: float,
    mask: MaskConfig | None,
) -> Dict[float, List[float]]:
    from collections import defaultdict

    lat_to_lons: Dict[float, set[float]] = defaultdict(set)

    def add_cells(
        region_lat_min: float,
        region_lat_max: float,
        region_lon_min: float,
        region_lon_max: float,
        step: float,
    ) -> None:
        lat_start = max(lat_min, region_lat_min)
        lat_stop = min(lat_max, region_lat_max)
        lon_start = max(lon_min, region_lon_min)
        lon_stop = min(lon_max, region_lon_max)
        if lat_start > lat_stop or lon_start > lon_stop:
            return
        for lat in _inclusive_range(lat_start, lat_stop, step):
            lon_set = lat_to_lons[lat]
            for lon in _inclusive_range(lon_start, lon_stop, step):
                lon_set.add(lon)

    base_step = fallback_step
    if mask:
        base_step = mask.default_step
    add_cells(lat_min, lat_max, lon_min, lon_max, base_step)

    if mask:
        for region in mask.regions:
            add_cells(region.lat_min, region.lat_max, region.lon_min, region.lon_max, region.step)

    coordinate_map: Dict[float, List[float]] = {}
    for lat, lon_values in lat_to_lons.items():
        coordinate_map[lat] = sorted(lon_values)
    return dict(sorted(coordinate_map.items()))


def steps_summary(mask: MaskConfig | None, fallback_step: float) -> List[float]:
    if mask:
        return mask.steps
    return [fallback_step]
