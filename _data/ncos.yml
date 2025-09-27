#!/usr/bin/env python3
"""
Generate _data/bhn_ncos_schedule.yml from _data/ncos.yml

Rules per date (next N Saturdays):
  1) If overrides has {date, callsign, note}, use that.
  2) Else use rotation by nth Saturday (1..5).
  3) If neither applies, write nco="TBD", unassigned=true, and log a notice/warning.

Extras:
  - By default, if today is Saturday and the net's local end time has passed,
    the script SKIPS today's row (so updates later in the day won't still show it).
    Control this via env SKIP_TODAY_AFTER_END: "1" (default) or "0".

  - The script NEVER fails the build for TBD unless STRICT_NCO=1 is set in the env.
    If STRICT_NCO=1 and any unassigned dates are present, exit code 1 is returned.

Output shape:
items:
  - date: "YYYY-MM-DD"
    nco: "CALLSIGN" | "TBD"
    notes: "<optional string, may be empty>"
    unassigned: true|false
"""

from __future__ import annotations

import os
import sys
import yaml
import calendar
from pathlib import Path
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# How many upcoming Saturdays to emit
N_DATES = 12


def find_repo_root(start: Path) -> Path:
    """
    Walk up from `start` until a folder containing _config.yml is found.
    Keeps the script robust when run from CI vs locally.
    """
    p = start.resolve()
    for anc in (p,) + tuple(p.parents):
        if (anc / "_config.yml").exists():
            return anc
    # Fall back to script dir if not found
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
    """Return 1..5 for the nth Saturday of the month for dt (which should be a Saturday)."""
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    sats = [
        d for d in cal.itermonthdates(dt.year, dt.month)
        if d.month == dt.month and d.weekday() == calendar.SATURDAY
    ]
    for i, d in enumerate(sats, start=1):
        if d == dt.date():
            return i
    return None


def next_saturday_on_or_after(dt: datetime) -> datetime:
    """Return the next Saturday at 00:00 local on/after dt."""
    d = dt
    while d.weekday() != calendar.SATURDAY:
        d += timedelta(days=1)
    return d.replace(hour=0, minute=0, second=0, microsecond=0)


def parse_hhmm(hhmm: str) -> time:
    hhmm = (hhmm or "").strip()
    try:
        h, m = hhmm.split(":")
        return time(int(h), int(m))
    except Exception:
        # Default 10:00 if malformed/missing
        return time(10, 0)


def main() -> int:
    here = Path(__file__).resolve().parent
    root = find_repo_root(here)

    ncos_file = root / "_data" / "ncos.yml"
    out_file = root / "_data" / "bhn_ncos_schedule.yml"

    print(f"[info] ROOT={root}")
    print(f"[info] NCOS_FILE={ncos_file}")
    print(f"[info] OUT_FILE={out_file}")
    print(f"[info] N_DATES={N_DATES}")

    data = load_yaml(ncos_file)

    # Timing/config
    tzname = data.get("time_zone", "America/New_York")
    tz = ZoneInfo(tzname)
    start_local = parse_hhmm(data.get("start_local", "10:00"))
    duration_min = int(data.get("duration_min", 60))

    now = datetime.now(tz)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    first_sat = next_saturday_on_or_after(today_midnight)

    # Rotation: normalize keys to int
    rotation_src = data.get("rotation") or {}
    rotation: dict[int, str] = {}
    for k, v in rotation_src.items():
        try:
            rotation[int(k)] = str(v).strip()
        except Exception:
            print(f"::warning ::rotation key not an int: {k!r} (ignored)")

    # Overrides: normalize and accept common typos for 'callsign'
    overrides_map: dict[str, dict[str, str]] = {}
    for item in (data.get("overrides") or []):
        dt = str(item.get("date") or "").strip()
        cs = (
            item.get("callsign")
            or item.get("call")
            or item.get("operator")
            or item.get("callssign")  # seen typo
        )
        if not dt or not cs:
            print(f"::warning ::bad override missing date/callsign: {item!r}")
            continue
        overrides_map[dt] = {
            "callsign": str(cs).strip(),
            "note": str(item.get("note", "") or "").strip(),
        }

    # Control flags
    skip_today_after_end = os.getenv("SKIP_TODAY_AFTER_END", "1") == "1"
    strict = os.getenv("STRICT_NCO", "0") == "1"

    items = []
    unassigned = []

    # Iterate Saturdays until we collect N_DATES rows (respecting 'skip today after end')
    candidate = first_sat
    while len(items) < N_DATES:
        date_key = candidate.strftime("%Y-%m-%d")

        # Skip "today" if it's already over and flag is on
        if candidate.date() == now.date() and skip_today_after_end:
            begin = datetime.combine(candidate.date(), start_local, tzinfo=tz)
            end = begin + timedelta(minutes=duration_min)
            if now >= end:
                print(f"[info] Skipping {date_key} (today's net has ended).")
                candidate += timedelta(days=7)
                continue

        # 1) overrides win
        ov = overrides_map.get(date_key)
        if ov:
            callsign = ov["callsign"]
            note = ov.get("note", "")
            is_unassigned = False
        else:
            # 2) rotation by nth Saturday
            nth = week_index_of_saturday(candidate)
            callsign = rotation.get(nth)
            note = ""
            if not callsign:
                # 3) no assignment → TBD (do NOT fail build)
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

        candidate += timedelta(days=7)

    dump_yaml(out_file, {"items": items})
    print(f"[ok] wrote {len(items)} items to {out_file}")

    if unassigned:
        dates_list = ", ".join(f"{d} (#{n})" for d, n in unassigned)
        print(f"::notice ::Unassigned dates included as TBD: {dates_list}")

    if strict and unassigned:
        # Fail only if STRICT_NCO=1
        print("::error ::Unassigned NCO dates present and STRICT_NCO=1 — failing build.")
        return 1

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as e:
        # Hard fail if the input YAML is missing — this is a real error.
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)
