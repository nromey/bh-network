#!/usr/bin/env python3
"""Generate _data/next_net.yml with upcoming Blind Hams Network nets."""
from __future__ import annotations

from dataclasses import dataclass
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterable, List
import argparse
import sys
import yaml

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo  # type: ignore


DEFAULT_TZ = "America/New_York"
HORIZON_DAYS = 60  # search window when finding upcoming occurrences
WEEK_WINDOW_DAYS = 7  # emit nets happening within this many days
SUPPORTED_FREQS = {"DAILY", "WEEKLY", "MONTHLY"}

DAY_CODES = {
    "MO": 0,
    "TU": 1,
    "WE": 2,
    "TH": 3,
    "FR": 4,
    "SA": 5,
    "SU": 6,
}


@dataclass
class Net:
    raw: dict
    id: str
    name: str
    description: str
    category: str
    start_local: time
    duration_min: int
    freq: str
    byday_codes: list[str]
    bysetpos: int | None
    tzname: str

    @classmethod
    def from_dict(cls, data: dict, default_tz: str) -> "Net | None":
        try:
            rid = str(data.get("id")).strip()
            if not rid:
                return None
            name = str(data.get("name") or "").strip()
            desc = str(data.get("description") or "").strip()
            cat = str(data.get("category") or "").strip()
            start_str = str(data.get("start_local") or "").strip() or "10:00"
            hh, mm = start_str.split(":")
            start_local = time(int(hh), int(mm))
            duration = int(data.get("duration_min") or 60)
            rrule = str(data.get("rrule") or "").strip().upper()
            parts = {}
            if rrule:
                for item in rrule.split(";"):
                    if "=" not in item:
                        continue
                    k, v = item.split("=", 1)
                    parts[k.strip().upper()] = v.strip()
            freq = parts.get("FREQ", "").upper() or "WEEKLY"
            if freq not in SUPPORTED_FREQS:
                return None
            byday = parts.get("BYDAY", "")
            byday_codes = [code.strip().upper() for code in byday.split(",") if code.strip()]
            bysetpos = parts.get("BYSETPOS")
            bysetpos_int = int(bysetpos) if bysetpos and bysetpos.lstrip("-").isdigit() else None
            tzname = str(data.get("time_zone") or default_tz or DEFAULT_TZ)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"::error ::Failed to parse net entry {data!r}: {exc}", file=sys.stderr)
            return None
        return cls(
            raw=data,
            id=rid,
            name=name,
            description=desc,
            category=cat.lower(),
            start_local=start_local,
            duration_min=duration,
            freq=freq,
            byday_codes=byday_codes,
            bysetpos=bysetpos_int,
            tzname=tzname,
        )


@dataclass
class Occurrence:
    net: Net
    start: datetime

    @property
    def end(self) -> datetime:
        return self.start + timedelta(minutes=self.net.duration_min)


def nth_weekday(year: int, month: int, weekday: int, ordinal: int) -> date | None:
    """Return the date of the nth weekday (ordinal can be negative for last)."""
    if ordinal == 0:
        return None

    # Build a list of all weekdays in the month matching `weekday`
    first_day = date(year, month, 1)
    days = []
    current = first_day
    while current.month == month:
        if current.weekday() == weekday:
            days.append(current)
        current += timedelta(days=1)
    if not days:
        return None

    if ordinal > 0:
        index = ordinal - 1
        if 0 <= index < len(days):
            return days[index]
    else:
        index = ordinal + len(days)
        if 0 <= index < len(days):
            return days[index]
    return None


def iter_daily(now: datetime, net: Net, horizon_days: int) -> Iterable[Occurrence]:
    for delta in range(horizon_days + 1):
        day = now.date() + timedelta(days=delta)
        start = datetime.combine(day, net.start_local, tzinfo=ZoneInfo(net.tzname))
        occ = Occurrence(net, start)
        # Keep occurrences whose end is still in the future
        if occ.end <= now:
            continue
        yield occ


def iter_weekly(now: datetime, net: Net, horizon_days: int) -> Iterable[Occurrence]:
    weekdays = [DAY_CODES.get(code) for code in net.byday_codes if DAY_CODES.get(code) is not None]
    if not weekdays:
        # Default to the weekday of the provided start date
        weekdays = [now.weekday()]
    for delta in range(horizon_days + 1):
        day = now.date() + timedelta(days=delta)
        if day.weekday() not in weekdays:
            continue
        start = datetime.combine(day, net.start_local, tzinfo=ZoneInfo(net.tzname))
        occ = Occurrence(net, start)
        if occ.end <= now:
            continue
        yield occ


def iter_monthly(now: datetime, net: Net, horizon_days: int) -> Iterable[Occurrence]:
    # When BYDAY missing, default to day-of-month of now
    tz = ZoneInfo(net.tzname)
    byday = net.byday_codes[0] if net.byday_codes else None
    target_weekday = DAY_CODES.get(byday) if byday else None
    ordinal = net.bysetpos or 1

    candidate = now
    # search month by month within horizon window
    months_to_check = max(1, horizon_days // 28 + 2)
    checked = 0
    while checked < months_to_check:
        year = candidate.year
        month = candidate.month
        if checked > 0:
            month += checked
            year += (month - 1) // 12
            month = ((month - 1) % 12) + 1
        if target_weekday is not None:
            occ_date = nth_weekday(year, month, target_weekday, ordinal)
        else:
            # fallback: use first day of month + ordinal-1 (clamped)
            try:
                occ_date = date(year, month, max(1, min(28, ordinal)))
            except ValueError:
                occ_date = None
        checked += 1
        if not occ_date:
            continue
        start = datetime.combine(occ_date, net.start_local, tz)
        occ = Occurrence(net, start)
        if occ.end <= now:
            continue
        yield occ


def upcoming_occurrences(net: Net, now: datetime, horizon_days: int) -> List[Occurrence]:
    if net.freq == "DAILY":
        iterator = iter_daily
    elif net.freq == "WEEKLY":
        iterator = iter_weekly
    elif net.freq == "MONTHLY":
        iterator = iter_monthly
    else:
        return []
    occs = list(iterator(now, net, horizon_days))
    occs.sort(key=lambda o: o.start)
    return occs


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing YAML file: {path}")
    with path.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp) or {}


def dump_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        yaml.safe_dump(data, fp, sort_keys=False, allow_unicode=False)


def build_next_net(
    root: Path,
    category: str,
    primary_category: str,
    horizon_days: int,
    week_window: int,
) -> dict:
    data = load_yaml(root / "_data" / "nets.yml")
    tzname = data.get("time_zone") or DEFAULT_TZ
    tz = ZoneInfo(tzname)
    now = datetime.now(tz)

    nets_raw = data.get("nets") or []
    nets: list[Net] = []
    for item in nets_raw:
        net = Net.from_dict(item, tzname)
        if not net:
            continue
        nets.append(net)

    category_value = (category or "").lower()
    primary_category = (primary_category or "").lower()

    category_filter = None if category_value == "all" else category_value

    all_occurrences: list[Occurrence] = []
    for net in nets:
        all_occurrences.extend(upcoming_occurrences(net, now, horizon_days))

    all_occurrences.sort(key=lambda o: o.start)

    def first_for_category(cat: str) -> Occurrence | None:
        cat = (cat or "").lower()
        if not cat:
            return None
        for occ in all_occurrences:
            if occ.net.category == cat:
                return occ
        return None

    next_occ = first_for_category(primary_category) or (all_occurrences[0] if all_occurrences else None)

    if category_filter:
        occurrences = [occ for occ in all_occurrences if occ.net.category == category_filter]
    else:
        occurrences = list(all_occurrences)

    week_cutoff = now + timedelta(days=week_window)
    week_occurrences = [occ for occ in occurrences if occ.start <= week_cutoff]

    def serialize_occ(occ: Occurrence) -> dict:
        # Pull commonly used connection fields directly from the raw net entry
        raw = occ.net.raw or {}
        connections = {
            "allstar": raw.get("allstar"),
            "echolink": raw.get("echolink"),
            "frequency": raw.get("frequency"),
            "mode": raw.get("mode"),
            "dmr": raw.get("dmr") or raw.get("DMR"),
            "dmr_system": raw.get("dmr_system") or raw.get("DMR_System"),
            "dmr_tg": raw.get("dmr_tg") or raw.get("DMR_TG"),
            "talkgroup": raw.get("talkgroup"),
            "peanut": raw.get("peanut"),
            "dstar": raw.get("dstar") or raw.get("DStar"),
            "ysf": raw.get("ysf"),
            "wiresx": raw.get("wiresx") or raw.get("wires_x"),
            "p25": raw.get("p25"),
            "nxdn": raw.get("nxdn"),
            "location": raw.get("location"),
            "website": raw.get("website"),
        }
        return {
            "id": occ.net.id,
            "name": occ.net.name,
            "description": occ.net.description,
            "category": occ.net.category,
            "start_local_iso": occ.start.isoformat(),
            "duration_min": occ.net.duration_min,
            "time_zone": occ.net.tzname,
            "connections": connections,
        }

    payload = {
        "time_zone": tzname,
    }
    # To avoid noisy commits, omit the timestamp by default.
    # Include it only if NEXT_NET_INCLUDE_TIMESTAMP=1
    if (os.getenv("NEXT_NET_INCLUDE_TIMESTAMP") or "0") == "1":
        payload["generated_at"] = now.isoformat()
    if next_occ:
        payload["next_net"] = serialize_occ(next_occ)
    else:
        payload["next_net"] = None
    payload["week"] = [serialize_occ(o) for o in week_occurrences]
    payload["categories"] = sorted({occ.net.category for occ in occurrences})
    payload["primary_category"] = primary_category
    defaults = [primary_category] if primary_category else []
    payload["default_categories"] = defaults
    return payload


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "_config.yml").exists():
            return candidate
    return start


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--category",
        default="all",
        help="Category filter for weekly list (default: all)",
    )
    parser.add_argument(
        "--primary-category",
        default="bhn",
        help="Category to highlight as the next net (default: bhn)",
    )
    parser.add_argument("--horizon-days", type=int, default=HORIZON_DAYS, help="Days to scan when finding next nets")
    parser.add_argument("--week-window", type=int, default=WEEK_WINDOW_DAYS, help="Days ahead to include in weekly list")
    args = parser.parse_args(argv)

    script_dir = Path(__file__).resolve().parent
    root = find_repo_root(script_dir)
    output_path = root / "_data" / "next_net.yml"

    payload = build_next_net(
        root,
        args.category,
        args.primary_category,
        args.horizon_days,
        args.week_window,
    )
    dump_yaml(output_path, payload)
    print(f"[info] Wrote {output_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
