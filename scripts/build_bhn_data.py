#!/usr/bin/env python3
"""
Generate _data/bhn_ncos_schedule.yml from _data/ncos.yml

- Lists the next N Saturdays in the configured time zone.
- For each date:
    1) If there's an overrides entry for that date, use its callsign and carry its note.
    2) Else pick from the 1..5 rotation by "nth Saturday of the month".
    3) If neither applies (e.g., 5th Saturday with no override), skip the date.
- Writes:
    items:
      - date: YYYY-MM-DD
        nco: <CALLSIGN>
        notes: <string, may be empty>
"""

from __future__ import annotations

import sys
import calendar
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

# How many upcoming Saturdays to emit
N_DATES = 12


def find_repo_root(start: Path) -> Path:
    """
    Walk upward until a folder containing _config.yml is found.
    Fallback to the starting directory if not found.
    """
    p = start.resolve()
    for anc in [p] + list(p.parents):
        if (anc / "_config.yml").exists():
            return anc
    print("[warn] _config.yml not found; using script directory")
    return p


def load_yaml(p: Path) -> dict:
    if not p.exists():
        raise FileNotFoundError(f"Missing input YAML: {p}")
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def dump_yaml(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)


def week_index_of_saturday(dt: datetime) -> int | None:
    """
    Return 1..5 for the nth Saturday of the month for dt (which should be a Saturday).
    """
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    sats = [
        d for d in cal.itermonthdates(dt.year, dt.month)
        if d.month == dt.month and d.weekday() == calendar.SATURDAY
    ]
    for i, d in enumerate(sats, start=1):
        if d == dt.date():
            return i
    return None


def next_saturdays(start_dt: datetime, count: int):
    """
    Yield 'count' Saturdays starting from start_dt (inclusive if Saturday).
    """
    d = start_dt
    while d.weekday() != calendar.SATURDAY:
        d += timedelta(days=1)
    for _ in range(count):
        yield d
        d += timedelta(days=7)


def main() -> int:
    here = Path(__file__).parent
    root = find_repo_root(here)

    ncos_file = root / "_data" / "ncos.yml"
    out_file = root / "_data" / "bhn_ncos_schedule.yml"

    print(f"[info] cwd        = {Path.cwd()}")
    print(f"[info] script dir = {here}")
    print(f"[info] repo root  = {root}")
    print(f"[info] NCOS_FILE  = {ncos_file}")
    print(f"[info] OUT_FILE   = {out_file}")
    print(f"[info] N_DATES    = {N_DATES}")

    data = load_yaml(ncos_file)

    # Time zone (defaults to America/New_York)
    tz = ZoneInfo(data.get("time_zone", "America/New_York"))
    today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

    # Rotation map: keys "1","2","3","4","5" or ints → int keys
    rotation_src = data.get("rotation") or {}
    rotation = {}
    for k, v in rotation_src.items():
        try:
            rotation[int(k)] = str(v).strip()
        except Exception:
            print(f"[warn] rotation key not an int: {k!r} (ignored)")

    # Overrides: date → {callsign, note}
    overrides_map: dict[str, dict[str, str]] = {}
    for item in (data.get("overrides") or []):
        dt = item.get("date")
        cs = item.get("callsign")
        if not dt or not cs:
            print(f"[warn] bad override missing date/callsign: {item!r}")
            continue
        overrides_map[str(dt)] = {
            "callsign": str(cs).strip(),
            "note": str(item.get("note", "") or "").strip(),
        }

    items = []
    for dt in next_saturdays(today, N_DATES):
        date_key = dt.strftime("%Y-%m-%d")

        # (1) Date-specific override
        ov = overrides_map.get(date_key)
        if ov:
            callsign = ov["callsign"]
            note = ov.get("note", "")
        else:
            # (2) Rotation by nth Saturday
            nth = week_index_of_saturday(dt)
            callsign = rotation.get(nth)
            note = ""

        # (3) Skip if no assignment (e.g., 5th Saturday without override)
        if callsign:
            items.append({"date": date_key, "nco": callsign, "notes": note})

    dump_yaml(out_file, {"items": items})
    print(f"[ok] wrote {len(items)} items to {out_file}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)
