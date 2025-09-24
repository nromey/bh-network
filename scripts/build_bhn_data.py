#!/usr/bin/env python3
import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import sys
import yaml

# How many upcoming Saturdays to list
N_DATES = 12

ROOT = Path(__file__).resolve().parents[1]
NCOS_FILE = ROOT / "_data" / "ncos.yml"
OUT_FILE  = ROOT / "_data" / "bhn_ncos_schedule.yml"

def load_yaml(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def dump_yaml(p: Path, obj):
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)

def week_index_of_saturday(dt: datetime) -> int | None:
    """
    Return 1..5 for the nth Saturday of the month for dt (which should be a Saturday).
    """
    c = calendar.Calendar(firstweekday=calendar.SUNDAY)
    sats = [d for d in c.itermonthdates(dt.year, dt.month)
            if d.month == dt.month and d.weekday() == calendar.SATURDAY]
    for i, d in enumerate(sats, start=1):
        if d == dt.date():
            return i
    return None

def next_saturdays(start_dt: datetime, count: int):
    """
    Yield upcoming Saturdays starting from start_dt (inclusive if Saturday).
    """
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

    rotation = {int(k): v for k, v in (data.get("rotation") or {}).items()}
    overrides_list = data.get("overrides") or []
    overrides = {item["date"]: item["callsign"] for item in overrides_list if "date" in item and "callsign" in item}

    items = []
    for dt in next_saturdays(today, N_DATES):
        date_key = dt.strftime("%Y-%m-%d")
        # 1) Date-specific override wins
        callsign = overrides.get(date_key)
        if not callsign:
            # 2) Otherwise use rotation by nth Saturday
            nth = week_index_of_saturday(dt)
            callsign = rotation.get(nth)

        # If you don't have a standing 5th-Saturday rotation and there's no override,
        # we simply skip that date (nothing written).
        if callsign:
            items.append({"date": date_key, "callsign": callsign})

    dump_yaml(OUT_FILE, {"items": items})

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)
