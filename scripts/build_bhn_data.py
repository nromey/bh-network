#!/usr/bin/env python3
import os
import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import sys
import yaml

# Default how many upcoming Saturdays to list (can override via env NCO_WEEKS)
N_DATES = int(os.getenv("NCO_WEEKS", "12"))

def find_repo_root(start: Path) -> Path:
    """Walk up from 'start' until a folder containing _config.yml is found."""
    p = start.resolve()
    for anc in [p] + list(p.parents):
        if (anc / "_config.yml").exists():
            return anc
    # Fail fast in CI if we somehow run outside the repo
    raise FileNotFoundError("Couldn't find _config.yml by walking up from script dir; run inside a repo checkout")

HERE = Path(__file__).parent
ROOT = find_repo_root(HERE)

NCOS_FILE = ROOT / "_data" / "ncos.yml"
OUT_FILE  = ROOT / "_data" / "bhn_ncos_schedule.yml"

print(f"[info] cwd        = {Path.cwd()}")
print(f"[info] script dir = {HERE}")
print(f"[info] repo root  = {ROOT}")
print(f"[info] NCOS_FILE  = {NCOS_FILE}")
print(f"[info] OUT_FILE   = {OUT_FILE}")
print(f"[info] N_DATES    = {N_DATES}")

def load_yaml(p: Path):
    if not p.exists():
        raise FileNotFoundError(f"Missing input YAML: {p}")
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def dump_yaml(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)

def week_index_of_saturday(dt: datetime) -> int | None:
    """Return 1..5 for the nth Saturday of the month for dt (dt should be a Saturday)."""
    c = calendar.Calendar(firstweekday=calendar.SUNDAY)
    sats = [d for d in c.itermonthdates(dt.year, dt.month)
            if d.month == dt.month and d.weekday() == calendar.SATURDAY]
    for i, d in enumerate(sats, start=1):
        if d == dt.date():
            return i
    return None  # 5th Saturday may not exist every month

def next_saturdays(start_dt: datetime, count: int):
    """Yield upcoming Saturdays starting from start_dt (inclusive if Saturday)."""
    d = start_dt
    while d.weekday() != calendar.SATURDAY:
        d += timedelta(days=1)
    for _ in range(count):
        yield d
        d += timedelta(days=7)

def main():
    data = load_yaml(NCOS_FILE)

    tzname = data.get("time_zone", "America/New_York")
    tz = ZoneInfo(tzname)
    today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

    # rotation: { "1": "K4ABC — Sam", "2": "W1XYZ — Pat", ... }
    rotation = {int(k): v for k, v in (data.get("rotation") or {}).items()}

    # overrides: [{date: "YYYY-MM-DD", callsign: "K4ABC — Sam"}, ...]
    overrides_list = data.get("overrides") or []
    overrides = {
        item["date"]: item["callsign"]
        for item in overrides_list
        if isinstance(item, dict) and "date" in item and "callsign" in item
    }

    items = []
    for dt in next_saturdays(today, N_DATES):
        date_key = dt.strftime("%Y-%m-%d")

        # 1) Date-specific override wins
        nco = overrides.get(date_key)

        # 2) Otherwise use rotation by nth Saturday
        if not nco:
            nth = week_index_of_saturday(dt)
            if nth is not None:
                nco = rotation.get(nth)

        # If no rotation for this nth Saturday and no override, skip that date.
        if nco:
            items.append({"date": date_key, "nco": nco})

    dump_yaml(OUT_FILE, {"items": items})
    print(f"[ok] wrote {len(items)} items to {OUT_FILE}")
    if not items:
        print("[warn] items list is empty (no overrides and no matching rotation?)")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)
