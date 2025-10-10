#!/usr/bin/env python3
"""
Emit bhn_nco_12w.json for the BHN NCO page.
Reads _data/bhn_ncos_schedule.yml (12 dates) and _data/ncos.yml (time/tz/duration).

Canonical fields:
  - Top-level: generated_at, tz, time_local, tz_full, items[]
  - Items: id, name, start_iso, end_iso, duration_min, date, local_date,
           local_time, location, nco, unassigned, notes, note

Back-compat retained: local_date (mirrors date), note (mirrors notes).
"""
from __future__ import annotations
import os, sys, json
from pathlib import Path
from datetime import datetime, timedelta, UTC, time as dtime
from zoneinfo import ZoneInfo

try:
    import yaml
except Exception as e:
    sys.stderr.write(f"[error] PyYAML not installed: {e}\n")
    sys.exit(2)

REPO_ROOT = Path(os.environ.get("BHN_REPO_ROOT", str(Path.home())))
DATA = REPO_ROOT / "_data"
SCHED = DATA / "bhn_ncos_schedule.yml"
NCOS  = DATA / "ncos.yml"

def load_yaml(p: Path):
    if not p.exists():
        raise FileNotFoundError(f"Missing input YAML: {p}")
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def parse_hhmm(s: str) -> dtime:
    try:
        h, m = s.strip().split(":"); return dtime(int(h), int(m))
    except Exception:
        return dtime(10, 0)

def tz_full_label(tzname: str) -> str:
    return {
        'America/New_York': 'Eastern',
        'America/Chicago': 'Central',
        'America/Denver': 'Mountain',
        'America/Los_Angeles': 'Pacific',
    }.get(tzname, tzname)

def main() -> int:
    sched = load_yaml(SCHED)        # {"items":[{"date","nco","notes","unassigned"}, ...]}
    meta  = load_yaml(NCOS)         # has: time_zone, start_local, duration_min, location

    tzname = meta.get("time_zone", "America/New_York")
    tz = ZoneInfo(tzname)
    start_local = parse_hhmm(meta.get("start_local", "10:00"))
    duration_min = int(meta.get("duration_min", 60))
    location = meta.get("location", "AllStar 50631 · DMR TG 31672 · Echolink *KV3T-L")

    time_local_str = f"{start_local.hour:02d}:{start_local.minute:02d}"
    tz_full = tz_full_label(tzname)

    out_items = []
    for row in (sched.get("items") or []):
        date_str = str(row.get("date") or "").strip()
        if not date_str:
            continue
        nco = str(row.get("nco") or "").strip().upper()
        unassigned = bool(row.get("unassigned", False))
        notes_val = str(row.get("notes") or str(row.get("note") or "")).strip()

        try:
            y, m, d = [int(x) for x in date_str.split("-")]
            start_dt = datetime(y, m, d, start_local.hour, start_local.minute, tzinfo=tz)
            end_dt = start_dt + timedelta(minutes=duration_min)
            start_iso = start_dt.isoformat()
            end_iso = end_dt.isoformat()
            local_date = start_dt.strftime("%Y-%m-%d")
            local_time = start_dt.strftime("%H:%M")
        except Exception:
            start_iso = end_iso = ""
            local_date = date_str
            local_time = time_local_str

        out_items.append({
            "id": "bhn-main",
            "name": "Blind Hams Digital Net",
            "start_iso": start_iso,
            "end_iso": end_iso,
            "duration_min": duration_min,
            "local_date": local_date,
            "date": local_date,          # canonical (mirror)
            "local_time": local_time,
            "location": location,
            "nco": nco,
            "unassigned": unassigned,
            "note": notes_val,           # back-compat
            "notes": notes_val           # canonical (mirror)
        })

    out = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tz": tzname,
        "time_local": time_local_str,
        "tz_full": tz_full,
        "items": out_items
    }
    json.dump(out, sys.stdout, ensure_ascii=False)
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)

