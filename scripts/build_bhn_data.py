#!/usr/bin/env python3
"""
Generate _data/bhn_ncos_schedule.yml from _data/ncos.yml
Logic per date (next N Saturdays):
  1) If override with {date, callsign, note} exists, use that.
  2) Else use rotation by nth Saturday (1..5).
  3) Else write nco="TBD", unassigned=true, notes explain why.
STRICT_NCO=1 -> exit 1 if any unassigned; STRICT_NCO=0 -> never fail.
"""

from __future__ import annotations
import os
import sys
import yaml
import calendar
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# How many upcoming Saturdays to emit
N_DATES = 12

def find_repo_root() -> Path:
    """Prefer GitHub workspace; else CWD; else walk up from script dir until _config.yml is found."""
    here = Path(__file__).resolve().parent
    # 1) GitHub Actions workspace if present
    gw = os.environ.get("GITHUB_WORKSPACE")
    if gw:
        root = Path(gw).resolve()
        if (root / "_config.yml").exists():
            return root
    # 2) Current working dir
    cwd = Path.cwd().resolve()
    if (cwd / "_config.yml").exists():
        return cwd
    # 3) Walk up from script dir
    for anc in [here] + list(here.parents):
        if (anc / "_config.yml").exists():
            return anc
    # 4) As a last resort, use script dir
    return here

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
    sats = [d for d in cal.itermonthdates(dt.year, dt.month)
            if d.month == dt.month and d.weekday() == calendar.SATURDAY]
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
    root = find_repo_root()
    ncos_file = root / "_data" / "ncos.yml"
    out_file  = root / "_data" / "bhn_ncos_schedule.yml"

    print(f"[info] PWD        = {Path.cwd()}")
    print(f"[info] HERE       = {Path(__file__).resolve().parent}")
    print(f"[info] ROOT       = {root}")
    print(f"[info] NCOS_FILE  = {ncos_file}")
    print(f"[info] OUT_FILE   = {out_file}")
    print(f"[info] N_DATES    = {N_DATES}")

    data = load_yaml(ncos_file)

    tz = ZoneInfo(data.get("time_zone", "America/New_York"))
    today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

    # rotation keys may be "1","2",..., turn into {1:"CALL", ...}
    rotation_src = data.get("rotation") or {}
    rotation: dict[int, str] = {}
    for k, v in rotation_src.items():
        try:
            rotation[int(k)] = str(v).strip()
        except Exception:
            print(f"::warning ::rotation key not an int: {k!r} (ignored)")

    # map overrides by ISO date
    overrides_map: dict[str, dict[str, str]] = {}
    for item in (data.get("overrides") or []):
        dt = (item.get("date") or "").strip()
        cs = (item.get("callsign") or "").strip()
        note = (item.get("note") or "").strip()
        if not dt or not cs:
            print(f"::warning ::bad override missing date/callsign: {item!r}")
            continue
        overrides_map[dt] = {"callsign": cs, "note": note}

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
                print(f"::notice ::{note} date={date_key}")
                callsign = "TBD"
                is_unassigned = True
                unassigned.append((date_key, nth))
            else:
                is_unassigned = False

        items.append({
            "date": date_key,
            "nco": callsign,
            "notes": note,
            "unassigned": bool(is_unassigned),
        })

    dump_yaml(out_file, {"items": items})
    print(f"[ok] wrote {len(items)} items to {out_file}")

    if unassigned:
        dates_list = ", ".join(f"{d} (#{n})" for d, n in unassigned)
        print(f"::notice ::Unassigned dates included as TBD: {dates_list}")

    strict = os.getenv("STRICT_NCO", "1") == "1"
    if strict and unassigned:
        return 1
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)
