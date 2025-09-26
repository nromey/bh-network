#!/usr/bin/env python3
"""
Generate _data/bhn_ncos_schedule.yml from _data/ncos.yml

- Next N Saturdays (TZ from _data/ncos.yml; defaults to America/New_York).
- Per date:
    1) If overrides has {date, callsign, note}, use that callsign + note.
    2) Else use rotation by nth Saturday (1..5).
    3) If neither applies, WRITE a row with nco="TBD", notes explaining why,
       and unassigned=true; also emit a GitHub Actions warning.

Output:
items:
  - date: YYYY-MM-DD
    nco: <CALLSIGN or "TBD">
    notes: <string, may be empty>
    unassigned: <true|false>
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

    tz = ZoneInfo(data.get("time_zone", "America/New_York"))
    today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

    rotation_src = data.get("rotation") or {}
    rotation: dict[int, str] = {}
    for k, v in rotation_src.items():
        try:
            rotation[int(k)] = str(v).strip()
        except Exception:
            print(f"::warning ::rotation key not an int: {k!r} (ignored)")

    overrides_map: dict[str, dict[str, str]] = {}
    for item in (data.get("overrides") or []):
        dt = item.get("date")
        cs = item.get("callsign")
        if not dt or not cs:
            print(f"::warning ::bad override missing date/callsign: {item!r}")
            continue
        overrides_map[str(dt)] = {
            "callsign": str(cs).strip(),
            "note": str(item.get("note", "") or "").strip(),
        }

    items = []
    unassigned = []

    for dt in next_saturdays(today, N_DATES):
        date_key = dt.strftime("%Y-%m-%d")

        ov = overrides_map.get(date_key)
        if ov:
            callsign = ov["callsign"]
            note = ov.get("note", "")
            is_unassigned = False
        else:
            nth = week_index_of_saturday(dt)
            callsign = rotation.get(nth)
            note = ""
            if not callsign:
                if nth == 5:
                    note = "No NCO assigned (5th Saturday). Please add an override in _data/ncos.yml."
                else:
                    note = f"No NCO assigned (nth Saturday #{nth}). Add an override or fill rotation[{nth}] in _data/ncos.yml."
                print(f"::warning ::{note} date={date_key}")
                callsign = "TBD"
                is_unassigned = True
                unassigned.append((date_key, nth))
            else:
                is_unassigned = False

        items.append({"date": date_key, "nco": callsign, "notes": note, "unassigned": bool(is_unassigned)})

    dump_yaml(out_file, {"items": items})
    print(f"[ok] wrote {len(items)} items to {out_file}")

    if unassigned:
        dates_list = ", ".join(f"{d} (#{n})" for d, n in unassigned)
        print(f"::notice ::Unassigned dates included as TBD: {dates_list}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)
