#!/usr/bin/env python3
"""Convert `_data/nets.yml` into a JSON file with the same structure.

This helper provides a deterministic baseline as we migrate the nets workflow
from YAML to JSON. It reads the existing YAML data, preserves the familiar key
ordering, and writes `_data/nets.json` for review.

Usage
=====

    python scripts/convert_nets_yaml_to_json.py \
        --input _data/nets.yml \
        --output _data/nets.json
"""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

import yaml

BASE_NET_KEYS = [
    "id",
    "category",
    "name",
    "description",
    "start_local",
    "time_zone",
    "duration_min",
    "rrule",
]

OPTIONAL_NET_KEYS = [
    "location",
    "mode",
    "dmr_system",
    "dmr_tg",
    "allstar",
    "echolink",
    "frequency",
    "dmr",
    "talkgroup",
    "dstar",
    "DStar",
    "peanut",
    "ysf",
    "wiresx",
    "wires_x",
    "p25",
    "nxdn",
    "website",
    "schedule_text",
]

TOP_LEVEL_ORDER = ["time_zone", "nets"]


def load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError:
        raise SystemExit(f"Input file not found: {path}")
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        raise SystemExit(f"Failed to parse YAML from {path}: {exc}") from exc


def dump_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def normalize_structure(raw: dict[str, Any]) -> OrderedDict:
    nets = raw.get("nets")
    if isinstance(nets, list):
        normalized_nets = []
        for entry in nets:
            if not isinstance(entry, dict):
                normalized_nets.append(entry)
                continue
            ordered = OrderedDict()
            for key in BASE_NET_KEYS:
                if key in entry:
                    ordered[key] = entry[key]
            for key in OPTIONAL_NET_KEYS:
                if key in entry and key not in ordered:
                    ordered[key] = entry[key]
            remaining = sorted(k for k in entry.keys() if k not in ordered)
            for key in remaining:
                ordered[key] = entry[key]
            normalized_nets.append(ordered)
        raw = raw.copy()
        raw["nets"] = normalized_nets

    ordered_top = OrderedDict()
    for key in TOP_LEVEL_ORDER:
        if key in raw:
            ordered_top[key] = raw[key]
    for key in sorted(raw.keys()):
        if key not in ordered_top:
            ordered_top[key] = raw[key]
    return ordered_top


def convert(input_path: Path, output_path: Path) -> None:
    data = load_yaml(input_path)
    if not isinstance(data, dict):
        raise SystemExit("Expected top-level mapping in nets YAML.")
    normalized = normalize_structure(data)
    dump_json(normalized, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert nets YAML to JSON.")
    parser.add_argument(
        "--input",
        default="_data/nets.yml",
        type=Path,
        help="Path to the YAML file (default: _data/nets.yml)",
    )
    parser.add_argument(
        "--output",
        default="_data/nets.json",
        type=Path,
        help="Destination JSON file (default: _data/nets.json)",
    )
    args = parser.parse_args()
    convert(args.input, args.output)


if __name__ == "__main__":  # pragma: no cover
    main()
