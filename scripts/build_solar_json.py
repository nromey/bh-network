#!/usr/bin/env python3
"""
Fetch real-time solar/geomagnetic indices from NOAA SWPC and write solar.json.

Outputs (default: data/solar.json) match the Blind Hams Solar project schema
draft: https://services.swpc.noaa.gov/ … (see docs/solar-agents.md §7.1).
Now includes daily sunspot numbers and NOAA flare/proton probabilities.

The script intentionally avoids third-party deps so it can run via cron on
minimal hosts (e.g., Andre's 3.onj.me VM). Use python3.11+ for zoneinfo.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

# --- Constants ----------------------------------------------------------------

SWPC_BASE = "https://services.swpc.noaa.gov"

SOURCES = {
    "f10_7": f"{SWPC_BASE}/json/f107_cm_flux.json",
    "kp": f"{SWPC_BASE}/json/planetary_k_index_1m.json",
    "boulder_k": f"{SWPC_BASE}/json/boulder_k_index_1m.json",
    "solar_wind": f"{SWPC_BASE}/json/ace/swepam/ace_swepam_1h.json",
    "xray": f"{SWPC_BASE}/json/goes/primary/xrays-1-day.json",
    "sunspot": f"{SWPC_BASE}/text/daily-solar-indices.txt",
    "flare_probs": f"{SWPC_BASE}/json/solar_probabilities.json",
    "wwv": f"{SWPC_BASE}/text/wwv.txt",
    "three_day": f"{SWPC_BASE}/text/3-day-forecast.txt",
    "geomag_forecast": f"{SWPC_BASE}/text/3-day-geomag-forecast.txt",
}

# Kp step (0..27) -> Ap value, per NOAA conversion table
KP_STEP_TO_AP = [
    0,   # 0o
    2,   # 0+
    3,   # 1-
    4,   # 1o
    5,   # 1+
    6,   # 2-
    7,   # 2o
    9,   # 2+
    12,  # 3-
    15,  # 3o
    18,  # 3+
    22,  # 4-
    27,  # 4o
    32,  # 4+
    39,  # 5-
    48,  # 5o
    56,  # 5+
    67,  # 6-
    80,  # 6o
    94,  # 6+
    111, # 7-
    132, # 7o
    154, # 7+
    179, # 8-
    207, # 8o
    236, # 8+
    300, # 9-
    400, # 9o
]

XRAY_BANDS = ("0.1-0.8nm", "0.05-0.4nm")

NOISE_LEVELS = [
    (0.0, 2.0, 0, "Baseline noise floor"),
    (2.0, 3.0, 1, "Slightly elevated noise (about plus one S-unit)"),
    (3.0, 4.0, 2, "Moderate noise rise (about plus two S-units)"),
    (4.0, 5.0, 3, "High noise (about plus three S-units)"),
    (5.0, 6.0, 4, "Strong storm noise (about plus four S-units)"),
    (6.0, 10.0, 5, "Severe noise (plus five S-units or more)"),
]

TEXT_SOURCES = {"sunspot", "wwv", "three_day", "geomag_forecast"}

MONTH_MAP = {
    "JAN": 1,
    "JANUARY": 1,
    "FEB": 2,
    "FEBRUARY": 2,
    "MAR": 3,
    "MARCH": 3,
    "APR": 4,
    "APRIL": 4,
    "MAY": 5,
    "JUN": 6,
    "JUNE": 6,
    "JUL": 7,
    "JULY": 7,
    "AUG": 8,
    "AUGUST": 8,
    "SEP": 9,
    "SEPT": 9,
    "SEPTEMBER": 9,
    "OCT": 10,
    "OCTOBER": 10,
    "NOV": 11,
    "NOVEMBER": 11,
    "DEC": 12,
    "DECEMBER": 12,
}


# --- Utility helpers ----------------------------------------------------------

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: str) -> datetime | None:
    """Parse SWPC timestamps (which may omit the trailing Z) as UTC."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso_z(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_json(url: str, timeout: float = 10.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "BlindHamsSolar/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"{url} -> HTTP {resp.status}")
        data = resp.read()
    try:
        text = data.decode("utf-8")
        return json.loads(text)
    except json.JSONDecodeError as exc:
        text = data.decode("utf-8", "replace")
        decoder = json.JSONDecoder()
        try:
            value, _ = decoder.raw_decode(text)
            return value
        except json.JSONDecodeError:
            raise RuntimeError(f"{url} -> invalid JSON: {exc}") from exc


def fetch_text(url: str, timeout: float = 10.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "BlindHamsSolar/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"{url} -> HTTP {resp.status}")
        data = resp.read()
    return data.decode("utf-8", "replace")


def round_step(value: float, step: float) -> float:
    return round(value / step) * step


def kp_to_ap(kp_value: float) -> int | None:
    if math.isnan(kp_value):
        return None
    index = int(round(kp_value * 3))
    index = max(0, min(index, len(KP_STEP_TO_AP) - 1))
    return KP_STEP_TO_AP[index]


def classify_xray_flux(flux_wm2: float | None) -> str | None:
    if not flux_wm2 or flux_wm2 <= 0:
        return None
    bands = [
        ("X", 1e-4),
        ("M", 1e-5),
        ("C", 1e-6),
        ("B", 1e-7),
        ("A", 1e-8),
    ]
    for letter, floor in bands:
        if flux_wm2 >= floor:
            magnitude = flux_wm2 / floor
            return f"{letter}{magnitude:.1f}"
    return "A0.0"


def describe_kp_value(kp_value: float | None) -> str | None:
    if kp_value is None or math.isnan(kp_value):
        return None
    if kp_value < 2:
        return "Quiet"
    if kp_value < 3:
        return "Unsettled"
    if kp_value < 4:
        return "Active"
    if kp_value < 5:
        return "Minor storm levels"
    if kp_value < 6:
        return "Moderate storm levels"
    if kp_value < 7:
        return "Strong storm levels"
    if kp_value < 8:
        return "Severe storm levels"
    return "Extreme storm levels"


def age_minutes(reference: datetime, sample: datetime | None) -> float:
    if sample is None:
        return float("inf")
    delta = reference - sample
    return max(delta.total_seconds() / 60.0, 0.0)


# --- Extractors ----------------------------------------------------------------

@dataclass
class Metric:
    """Container for each metric with timestamp."""

    data: dict[str, Any]
    updated: datetime | None


def extract_sfi(raw: Iterable[dict[str, Any]]) -> Metric:
    latest = None
    latest_dt = None

    for row in raw:
        if row.get("frequency") != 2800:
            continue
        dt = parse_time(row.get("time_tag"))
        # Prefer the most recent row; tie-break on schedule (Noon > Afternoon > Morning)
        schedule = row.get("reporting_schedule") or ""
        schedule_rank = {"Noon": 3, "Afternoon": 2, "Morning": 1}.get(schedule, 0)
        if latest_dt is None or (dt and dt > latest_dt) or (
            dt == latest_dt and schedule_rank > (latest or {}).get("_schedule_rank", -1)
        ):
            latest = dict(row)
            latest["_schedule_rank"] = schedule_rank
            latest_dt = dt

    if not latest:
        return Metric({"value": None}, None)

    value = latest.get("flux")
    ninety_day = latest.get("ninety_day_mean")
    schedule = latest.get("reporting_schedule")

    metric = {
        "value": value if value is None else round(float(value), 1),
        "ninety_day_mean": ninety_day if ninety_day is None else round(float(ninety_day), 1),
        "schedule": schedule,
        "source": "SWPC f107_cm_flux.json",
    }

    if latest_dt:
        metric["time_tag"] = iso_z(latest_dt)

    return Metric(metric, latest_dt)


def extract_kp(raw: Iterable[dict[str, Any]], source_label: str) -> Metric:
    latest = None
    latest_dt = None
    for row in raw:
        dt = parse_time(row.get("time_tag"))
        if latest_dt is None or (dt and dt > latest_dt):
            latest = row
            latest_dt = dt

    if not latest:
        return Metric({"value": None}, None)

    kp_est = latest.get("estimated_kp")
    kp_index = latest.get("kp_index")
    kp_code = latest.get("kp")

    if kp_est is not None:
        kp_est = round_step(float(kp_est), 1 / 3)

    ap_value = kp_to_ap(kp_est) if kp_est is not None else None

    metric = {
        "value": kp_est,
        "kp_index": kp_index,
        "kp_code": kp_code,
        "ap": ap_value,
        "source": source_label,
    }

    if latest_dt:
        metric["time_tag"] = iso_z(latest_dt)

    return Metric(metric, latest_dt)


def extract_solar_wind(raw: Iterable[dict[str, Any]]) -> Metric:
    latest = None
    latest_dt = None
    for row in raw:
        dt = parse_time(row.get("time_tag"))
        if latest_dt is None or (dt and dt > latest_dt):
            latest = row
            latest_dt = dt

    if not latest:
        return Metric({}, None)

    metric = {
        "speed_kms": _safe_round(latest.get("speed"), 1),
        "density": _safe_round(latest.get("dens"), 3),
        "temperature": _safe_round(latest.get("temperature"), 0),
        "spacecraft": "ACE",
        "quality_flag": latest.get("dsflag"),
        "source": "SWPC ace_swepam_1h.json",
    }
    if latest_dt:
        metric["time_tag"] = iso_z(latest_dt)
    return Metric(metric, latest_dt)


def extract_xray(raw: Iterable[dict[str, Any]]) -> Metric:
    latest_by_energy: dict[str, tuple[dict[str, Any], datetime | None]] = {}
    for row in raw:
        energy = row.get("energy")
        if energy not in XRAY_BANDS:
            continue
        dt = parse_time(row.get("time_tag"))
        if energy not in latest_by_energy or (
            dt and latest_by_energy[energy][1] and dt > latest_by_energy[energy][1]
        ) or (energy not in latest_by_energy and dt):
            latest_by_energy[energy] = (row, dt)

    primary = latest_by_energy.get("0.1-0.8nm")
    secondary = latest_by_energy.get("0.05-0.4nm")

    chosen = primary or secondary
    if not chosen:
        return Metric({}, None)

    base_row, base_dt = chosen
    base_flux = base_row.get("flux")
    metric = {
        "flux_wm2": base_flux if base_flux is None else float(base_flux),
        "classification": classify_xray_flux(float(base_flux) if base_flux is not None else None),
        "energy": base_row.get("energy"),
        "satellite": base_row.get("satellite"),
        "source": "SWPC goes/primary/xrays-1-day.json",
    }

    if primary and secondary:
        alt_row, alt_dt = secondary if chosen is primary else primary
        alt_flux = alt_row.get("flux")
        metric["secondary"] = {
            "flux_wm2": alt_flux if alt_flux is None else float(alt_flux),
            "classification": classify_xray_flux(float(alt_flux) if alt_flux is not None else None),
            "energy": alt_row.get("energy"),
            "satellite": alt_row.get("satellite"),
            "time_tag": iso_z(alt_dt),
        }

    if base_dt:
        metric["time_tag"] = iso_z(base_dt)

    return Metric(metric, base_dt)


def _safe_round(value: Any, digits: int) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        iv = int(value)
    except (TypeError, ValueError):
        return None
    if iv in (-999, -1):
        return None
    return iv


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_month_name(value: str | None) -> int | None:
    if not value:
        return None
    key = value.strip().upper()
    return MONTH_MAP.get(key)


def parse_day_range(header: str, default_year: int) -> list[str]:
    """Parse ranges like 'Oct 15-Oct 17 2025' into ISO date strings."""
    header = header.strip()
    range_match = re.search(
        r"([A-Za-z]+)\s+(\d{1,2})\s*-\s*([A-Za-z]+)\s+(\d{1,2})\s+(\d{4})",
        header,
    )
    if range_match:
        start_month = parse_month_name(range_match.group(1))
        start_day = int(range_match.group(2))
        end_month = parse_month_name(range_match.group(3))
        end_day = int(range_match.group(4))
        year = int(range_match.group(5))
    else:
        alt_match = re.search(r"([A-Za-z]+)\s+(\d{1,2})\s*-\s*(\d{1,2})\s+(\d{4})", header)
        if not alt_match:
            return []
        start_month = parse_month_name(alt_match.group(1))
        start_day = int(alt_match.group(2))
        end_month = start_month
        end_day = int(alt_match.group(3))
        year = int(alt_match.group(4))
    if start_month is None or end_month is None:
        return []
    start_year = year or default_year
    end_year = year or default_year
    if end_month < start_month:
        end_year += 1
    start_date = datetime(start_year, start_month, start_day).date()
    end_date = datetime(end_year, end_month, end_day).date()
    dates: list[str] = []
    current = start_date
    while current <= end_date:
        dates.append(current.isoformat())
        current += timedelta(days=1)
    return dates


SMALL_NUM_WORDS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]

TENS_WORDS = {
    20: "twenty",
    30: "thirty",
    40: "forty",
    50: "fifty",
    60: "sixty",
    70: "seventy",
    80: "eighty",
    90: "ninety",
}

ORDINAL_BASE = {
    0: "zeroth",
    1: "first",
    2: "second",
    3: "third",
    4: "fourth",
    5: "fifth",
    6: "sixth",
    7: "seventh",
    8: "eighth",
    9: "ninth",
    10: "tenth",
    11: "eleventh",
    12: "twelfth",
    13: "thirteenth",
    14: "fourteenth",
    15: "fifteenth",
    16: "sixteenth",
    17: "seventeenth",
    18: "eighteenth",
    19: "nineteenth",
}

ORDINAL_TENS = {
    20: "twentieth",
    30: "thirtieth",
    40: "fortieth",
    50: "fiftieth",
    60: "sixtieth",
    70: "seventieth",
    80: "eightieth",
    90: "ninetieth",
}


def int_to_words(value: int) -> str:
    if value == 0:
        return SMALL_NUM_WORDS[0]
    if value < 0:
        return "negative " + int_to_words(-value)

    parts: list[str] = []
    for magnitude, label in ((1_000_000_000, "billion"), (1_000_000, "million"), (1000, "thousand")):
        if value >= magnitude:
            count = value // magnitude
            parts.append(f"{int_to_words(count)} {label}")
            value %= magnitude

    if value >= 100:
        hundreds = value // 100
        parts.append(f"{SMALL_NUM_WORDS[hundreds]} hundred")
        value %= 100

    if value >= 20:
        tens = (value // 10) * 10
        remainder = value % 10
        if remainder:
            parts.append(f"{TENS_WORDS[tens]}-{SMALL_NUM_WORDS[remainder]}")
        else:
            parts.append(TENS_WORDS[tens])
        value = 0

    if 0 < value < 20:
        parts.append(SMALL_NUM_WORDS[value])

    return " ".join(parts)


def digits_to_words(sequence: str) -> str:
    return " ".join(SMALL_NUM_WORDS[int(ch)] for ch in sequence if ch.isdigit())


def decimal_to_words(value: Any, digits: int = 1) -> str | None:
    num = _safe_float(value)
    if num is None or math.isnan(num):
        return None

    sign = ""
    if num < 0:
        sign = "negative "
        num = abs(num)

    digits = max(digits, 0)
    formatted = f"{num:.{digits}f}"
    if "." not in formatted:
        integer_part = int(round(num))
        return f"{sign}{int_to_words(integer_part)}"

    integer_str, fractional_str = formatted.split(".")
    fractional_str = fractional_str.rstrip("0")
    integer_part = int(integer_str) if integer_str else 0
    integer_words = int_to_words(integer_part)

    if not fractional_str:
        return f"{sign}{integer_words}"

    fractional_words = digits_to_words(fractional_str)
    return f"{sign}{integer_words} point {fractional_words}"


def ordinal_word(value: int) -> str:
    if value in ORDINAL_BASE:
        return ORDINAL_BASE[value]
    if value in ORDINAL_TENS:
        return ORDINAL_TENS[value]
    if value < 0:
        return "negative " + ordinal_word(-value)

    tens = (value // 10) * 10
    remainder = value % 10
    if remainder == 0:
        return ORDINAL_TENS.get(tens, f"{int_to_words(value)}th")
    if tens:
        base = TENS_WORDS.get(tens, int_to_words(tens))
        suffix = ORDINAL_BASE.get(remainder, f"{int_to_words(remainder)}th")
        return f"{base}-{suffix}"
    return ORDINAL_BASE.get(remainder, f"{int_to_words(remainder)}th")


def year_to_words(year: int) -> str:
    if 2000 <= year <= 2099:
        if year == 2000:
            return "two thousand"
        remainder = year - 2000
        remainder_words = int_to_words(remainder)
        return f"twenty {remainder_words}"
    return int_to_words(year)


def format_decimal_words(value: Any, digits: int = 1) -> str | None:
    return decimal_to_words(value, digits)


def format_int_words(value: Any) -> str | None:
    iv = _safe_int(value)
    if iv is None:
        return None
    return int_to_words(iv)


def format_scientific_words(value: Any, digits: int = 2) -> str | None:
    num = _safe_float(value)
    if num is None or num == 0:
        return None
    mantissa_str, exponent_str = f"{num:.{digits}e}".split("e")
    mantissa_fractional = mantissa_str.split(".")[1].rstrip("0") if "." in mantissa_str else ""
    mantissa_digits = len(mantissa_fractional)
    mantissa_words = decimal_to_words(float(mantissa_str), mantissa_digits)
    exponent = int(exponent_str)
    if exponent == 0:
        return mantissa_words
    exponent_phrase = ""
    if exponent > 0:
        exponent_phrase = f"{ordinal_word(exponent)} power"
    else:
        exponent_phrase = f"negative {ordinal_word(abs(exponent))} power"
    return f"{mantissa_words} times ten to the {exponent_phrase}"


def format_decimal(value: Any, digits: int = 1) -> str | None:
    num = _safe_float(value)
    if num is None or math.isnan(num):
        return None
    formatted = f"{num:.{digits}f}"
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted


def format_int(value: Any) -> str | None:
    iv = _safe_int(value)
    if iv is None:
        return None
    return f"{iv:,}"


def format_scientific(value: Any, digits: int = 2) -> str | None:
    num = _safe_float(value)
    if num is None or num == 0:
        return None
    mantissa, exponent = f"{num:.{digits}e}".split("e")
    exp_int = int(exponent)
    sign = "minus " if exp_int < 0 else ""
    exp_abs = abs(exp_int)
    return f"{mantissa} times 10 to the {sign}{exp_abs}"


def estimate_noise(k_value: Any) -> dict[str, Any] | None:
    val = _safe_float(k_value)
    if val is None:
        return None
    for low, high, s_units, description in NOISE_LEVELS:
        if low <= val < high:
            return {
                "s_units": s_units,
                "description": description,
            }
    return {
        "s_units": NOISE_LEVELS[-1][2],
        "description": NOISE_LEVELS[-1][3],
    }


def extract_sunspot(text: str) -> Metric:
    if not text:
        return Metric({}, None)
    lines = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        if raw.startswith("#") or raw.startswith(":"):
            continue
        lines.append(raw)
    for raw in reversed(lines):
        parts = raw.split()
        if len(parts) < 7:
            continue
        try:
            year, month, day = map(int, parts[:3])
        except ValueError:
            continue
        updated = datetime(year, month, day, tzinfo=timezone.utc)
        number = _safe_int(parts[4]) if len(parts) > 4 else None
        area = _safe_int(parts[5]) if len(parts) > 5 else None
        new_regions = _safe_int(parts[6]) if len(parts) > 6 else None
        metric = {
            "number": number,
            "area_10e6": area,
            "new_regions": new_regions,
            "observation_date": f"{year:04d}-{month:02d}-{day:02d}",
            "source": "SWPC daily-solar-indices.txt",
        }
        return Metric(metric, updated)
    return Metric({}, None)


def extract_flare_probabilities(raw: Iterable[dict[str, Any]]) -> Metric:
    latest = None
    latest_dt = None
    for row in raw:
        dt = parse_time(row.get("date"))
        if latest_dt is None or (dt and dt > latest_dt):
            latest = row
            latest_dt = dt
    if not latest:
        return Metric({}, None)
    prob = {
        "c_class": {
            "day1": latest.get("c_class_1_day"),
            "day2": latest.get("c_class_2_day"),
            "day3": latest.get("c_class_3_day"),
        },
        "m_class": {
            "day1": latest.get("m_class_1_day"),
            "day2": latest.get("m_class_2_day"),
            "day3": latest.get("m_class_3_day"),
        },
        "x_class": {
            "day1": latest.get("x_class_1_day"),
            "day2": latest.get("x_class_2_day"),
            "day3": latest.get("x_class_3_day"),
        },
        "proton_10mev": {
            "day1": latest.get("10mev_protons_1_day"),
            "day2": latest.get("10mev_protons_2_day"),
            "day3": latest.get("10mev_protons_3_day"),
        },
        "polar_cap_absorption": latest.get("polar_cap_absorption"),
        "source": "SWPC solar_probabilities.json",
    }
    if latest_dt:
        prob["generated"] = iso_z(latest_dt)
    return Metric(prob, latest_dt)


def parse_wwv(text: str, default_year: int) -> dict[str, Any]:
    if not text or not text.strip():
        return {}
    data: dict[str, Any] = {}
    working_year = default_year

    issued_match = re.search(
        r":Issued:\s+(\d{4})\s+([A-Za-z]+)\s+(\d{1,2})\s+(\d{4})\s+UTC",
        text,
    )
    if issued_match:
        issued_year = int(issued_match.group(1))
        issued_month = parse_month_name(issued_match.group(2))
        issued_day = int(issued_match.group(3))
        issued_time = issued_match.group(4)
        if issued_month:
            issued_hour = int(issued_time[:2])
            issued_minute = int(issued_time[2:])
            issued_dt = datetime(
                issued_year,
                issued_month,
                issued_day,
                issued_hour,
                issued_minute,
                tzinfo=timezone.utc,
            )
            data["issued"] = iso_z(issued_dt)
            working_year = issued_year

    flux_match = re.search(
        r"Solar flux\s+(\d+)\s+and estimated planetary A-index\s+(\d+)",
        text,
        re.IGNORECASE,
    )
    if flux_match:
        data["solar_flux"] = int(flux_match.group(1))
        data["estimated_planetary_a_index"] = int(flux_match.group(2))

    k_match = re.search(
        r"estimated planetary K-index at\s+(\d{2})(\d{2})\s+UTC on\s+(\d{1,2})\s+([A-Za-z]+)\s+was\s+([\d.]+)",
        text,
        re.IGNORECASE,
    )
    if k_match:
        hour = int(k_match.group(1))
        minute = int(k_match.group(2))
        day = int(k_match.group(3))
        month = parse_month_name(k_match.group(4))
        value_str = k_match.group(5).strip().rstrip(".")
        entry: dict[str, Any] = {}
        try:
            entry["value"] = float(value_str)
        except ValueError:
            pass
        if month:
            k_dt = datetime(
                working_year,
                month,
                day,
                hour,
                minute,
                tzinfo=timezone.utc,
            )
            entry["time_tag"] = iso_z(k_dt)
        if entry:
            data["estimated_planetary_k_index"] = entry

    space_past = re.search(
        r"Space weather for the past 24 hours has been\s+(.+?)\.",
        text,
        re.IGNORECASE,
    )
    space_next = re.search(
        r"Space weather for the next 24 hours is predicted to be\s+(.+?)\.",
        text,
        re.IGNORECASE,
    )
    if space_past or space_next:
        space: dict[str, Any] = {}
        if space_past:
            space["past"] = space_past.group(1).strip()
        if space_next:
            space["next"] = space_next.group(1).strip()
        data["space_weather"] = space

    radio_matches = list(
        re.finditer(
            r"Radio blackouts reaching the\s+(R\d(?:-R\d)?)\s+level\s+(.+?)\.",
            text,
            re.IGNORECASE,
        )
    )
    if radio_matches:
        radio: dict[str, Any] = {}
        for idx, match in enumerate(radio_matches):
            level = match.group(1).upper()
            desc_raw = match.group(2).strip()
            desc_lower = desc_raw.lower()
            status: str | None = None
            if desc_lower.startswith("are "):
                status = desc_lower[4:]
            elif desc_lower.startswith("were "):
                status = desc_lower[5:]
            elif desc_lower.startswith("is "):
                status = desc_lower[3:]
            elif desc_lower in {"occurred", "observed"}:
                status = "occurred"
            else:
                status = desc_lower
            entry = {"level": level, "status": status, "text": desc_raw}
            if idx == 0:
                radio["past"] = entry
            else:
                radio["next"] = entry
        data["radio_blackouts"] = radio
    return data


def parse_three_day_forecast(text: str, default_year: int) -> dict[str, Any]:
    if not text or not text.strip():
        return {}
    result: dict[str, Any] = {}
    geomag: dict[str, Any] = {}
    solar: dict[str, Any] = {}
    radio: dict[str, Any] = {}
    year = default_year

    issued_match = re.search(
        r":Issued:\s+(\d{4})\s+([A-Za-z]+)\s+(\d{1,2})\s+(\d{4})\s+UTC",
        text,
    )
    if issued_match:
        issued_year = int(issued_match.group(1))
        issued_month = parse_month_name(issued_match.group(2))
        issued_day = int(issued_match.group(3))
        issued_time = issued_match.group(4)
        if issued_month:
            hour = int(issued_time[:2])
            minute = int(issued_time[2:])
            issued_dt = datetime(
                issued_year,
                issued_month,
                issued_day,
                hour,
                minute,
                tzinfo=timezone.utc,
            )
            result["issued"] = iso_z(issued_dt)
            year = issued_year

    lines = text.splitlines()
    current_section: str | None = None
    i = 0
    dates_cache: dict[str, list[str]] = {}

    def parse_percentage_row(parts: list[str], dates: list[str]) -> dict[str, Any]:
        label = parts[0]
        values: list[dict[str, Any]] = []
        for idx, cell in enumerate(parts[1 : len(dates) + 1]):
            match = re.match(r"(\d+)%", cell)
            if not match:
                continue
            values.append({"date": dates[idx], "percent": int(match.group(1))})
        return {"label": label, "values": values}

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("The greatest observed 3 hr Kp"):
            val_match = re.search(r"was\s+([0-9.]+)", line)
            if val_match:
                geomag["max_observed_kp"] = float(val_match.group(1))
        elif line.startswith("The greatest expected 3 hr Kp"):
            val_match = re.search(r"is\s+([0-9.]+)\s+\(NOAA Scale\s+(G\d)\)", line)
            if val_match:
                geomag["max_expected_kp"] = float(val_match.group(1))
                geomag["max_expected_scale"] = val_match.group(2)
        elif line.startswith("NOAA Kp index breakdown"):
            current_section = "geomagnetic"
            date_header = line.replace("NOAA Kp index breakdown", "").strip()
            dates = parse_day_range(date_header, year)
            dates_cache["geomagnetic"] = dates
            breakdown: list[dict[str, Any]] = []
            i += 1
            while i < len(lines) and lines[i].strip():
                parts = re.split(r"\s{2,}", lines[i].strip())
                if len(parts) >= len(dates) + 1:
                    range_label = parts[0]
                    values: list[dict[str, Any]] = []
                    for idx, cell in enumerate(parts[1 : len(dates) + 1]):
                        match = re.match(r"(?P<value>\d+(?:\.\d+)?)(?:\s*\((?P<scale>G\d)\))?", cell)
                        if not match:
                            continue
                        entry = {
                            "date": dates[idx],
                            "kp": float(match.group("value")),
                            "scale": match.group("scale"),
                        }
                        values.append(entry)
                    breakdown.append({"range": range_label, "values": values})
                i += 1
            geomag["kp_breakdown"] = breakdown
            continue
        elif line.startswith("Solar Radiation Storm Forecast"):
            current_section = "solar_radiation"
            date_header = line.split("for", 1)[1].strip()
            dates = parse_day_range(date_header, year)
            dates_cache["solar_radiation"] = dates
            rows: list[dict[str, Any]] = []
            i += 1
            while i < len(lines) and lines[i].strip():
                parts = re.split(r"\s{2,}", lines[i].strip())
                if len(parts) >= len(dates) + 1:
                    rows.append(parse_percentage_row(parts, dates))
                i += 1
            solar["probabilities"] = rows
            continue
        elif line.startswith("Radio Blackout Forecast"):
            current_section = "radio_blackout"
            date_header = line.split("for", 1)[1].strip()
            dates = parse_day_range(date_header, year)
            dates_cache["radio_blackout"] = dates
            rows: list[dict[str, Any]] = []
            i += 1
            while i < len(lines) and lines[i].strip():
                parts = re.split(r"\s{2,}", lines[i].strip())
                if len(parts) >= len(dates) + 1:
                    rows.append(parse_percentage_row(parts, dates))
                i += 1
            radio["probabilities"] = rows
            continue
        elif line.startswith("Rationale:"):
            rationale_lines = [line.split(":", 1)[1].strip()]
            i += 1
            while i < len(lines) and lines[i].strip():
                rationale_lines.append(lines[i].strip())
                i += 1
            rationale_text = " ".join(rationale_lines).strip()
            if current_section == "geomagnetic":
                geomag["rationale"] = rationale_text
            elif current_section == "solar_radiation":
                solar["rationale"] = rationale_text
            elif current_section == "radio_blackout":
                radio["rationale"] = rationale_text
            continue
        i += 1

    if geomag:
        result["geomagnetic"] = geomag
    if solar:
        result["solar_radiation"] = solar
    if radio:
        days: list[dict[str, Any]] = []
        probabilities = radio.get("probabilities", [])
        if probabilities:
            by_date: dict[str, dict[str, Any]] = {}
            for row in probabilities:
                label = row["label"]
                for entry in row["values"]:
                    by_date.setdefault(entry["date"], {})[label] = entry["percent"]
            for date in sorted(by_date.keys()):
                day_entry = {"date": date}
                day_entry.update(by_date[date])
                days.append(day_entry)
        if days:
            radio["days"] = days
        result["radio_blackout"] = radio

    return result


def parse_geomag_forecast(text: str, default_year: int) -> dict[str, Any]:
    if not text or not text.strip():
        return {}
    result: dict[str, Any] = {}
    year = default_year
    issued_match = re.search(
        r":Issued:\s+(\d{4})\s+([A-Za-z]+)\s+(\d{1,2})\s+(\d{4})\s+UTC",
        text,
    )
    if issued_match:
        issued_year = int(issued_match.group(1))
        issued_month = parse_month_name(issued_match.group(2))
        issued_day = int(issued_match.group(3))
        issued_time = issued_match.group(4)
        if issued_month:
            issued_dt = datetime(
                issued_year,
                issued_month,
                issued_day,
                int(issued_time[:2]),
                int(issued_time[2:]),
                tzinfo=timezone.utc,
            )
            result["issued"] = iso_z(issued_dt)
            year = issued_year

    lines = text.splitlines()
    ap_data: dict[str, Any] = {}
    probabilities: list[dict[str, Any]] = []
    kp_breakdown: list[dict[str, Any]] = []

    def parse_ap_line(line: str, key: str) -> None:
        match = re.search(rf"{key} Ap\s+(\d{{1,2}})\s+([A-Za-z]+)\s+(\d{{3}})", line)
        if match:
            day = int(match.group(1))
            month = parse_month_name(match.group(2))
            value = int(match.group(3))
            if month:
                dt = datetime(year, month, day).date()
                ap_data[key.lower()] = {"date": dt.isoformat(), "value": value}

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Observed Ap"):
            parse_ap_line(stripped, "Observed")
        elif stripped.startswith("Estimated Ap"):
            parse_ap_line(stripped, "Estimated")
        elif stripped.startswith("Predicted Ap"):
            match = re.search(
                r"Predicted Ap\s+(\d{1,2})\s+([A-Za-z]+)\s*-\s*(\d{1,2})\s+([A-Za-z]+)?\s+([0-9-]+)",
                stripped,
            )
            if match:
                start_day = int(match.group(1))
                start_month = parse_month_name(match.group(2))
                end_day = int(match.group(3))
                end_month = parse_month_name(match.group(4)) if match.group(4) else start_month
                values = [int(v) for v in match.group(5).split("-") if v.isdigit()]
                if start_month and end_month:
                    date_header = f"{match.group(2)} {start_day}-{match.group(4) or match.group(2)} {end_day} {year}"
                    dates = parse_day_range(date_header, year)
                    predicted = []
                    for idx2, date in enumerate(dates):
                        if idx2 < len(values):
                            predicted.append({"date": date, "value": values[idx2]})
                    ap_data["predicted"] = predicted
        elif stripped.startswith("NOAA Geomagnetic Activity Probabilities"):
            date_header = stripped.replace("NOAA Geomagnetic Activity Probabilities", "").strip()
            dates = parse_day_range(date_header, year)
            j = idx + 1
            while j < len(lines) and lines[j].strip():
                parts = re.split(r"\s{2,}", lines[j].strip())
                if len(parts) >= 2:
                    values = parts[1].split("/")
                    probs = []
                    for d_idx, value in enumerate(values):
                        if d_idx < len(dates) and value.isdigit():
                            probs.append({"date": dates[d_idx], "percent": int(value)})
                    probabilities.append({"label": parts[0], "values": probs})
                j += 1
        elif stripped.startswith("NOAA Kp index forecast"):
            date_header = stripped.replace("NOAA Kp index forecast", "").strip()
            dates = parse_day_range(date_header, year)
            j = idx + 1
            while j < len(lines) and lines[j].strip():
                parts = re.split(r"\s{2,}", lines[j].strip())
                if len(parts) >= len(dates) + 1:
                    range_label = parts[0]
                    values: list[dict[str, Any]] = []
                    for d_idx, cell in enumerate(parts[1 : len(dates) + 1]):
                        match_val = re.match(r"(\d+(?:\.\d+)?)", cell)
                        if not match_val:
                            continue
                        values.append({"date": dates[d_idx], "kp": float(match_val.group(1))})
                    kp_breakdown.append({"range": range_label, "values": values})
                j += 1

    if ap_data:
        result["ap"] = ap_data
    if probabilities:
        result["geomagnetic_activity"] = probabilities
    if kp_breakdown:
        result["kp_breakdown"] = kp_breakdown
    return result


# --- Assembly ------------------------------------------------------------------

def build_payload(
    now: datetime,
    metrics: dict[str, Metric],
    errors: list[str],
    flare_metric: Metric | None = None,
    wwv_report: dict[str, Any] | None = None,
    three_day_forecast: dict[str, Any] | None = None,
    geomag_forecast: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ages = [
        age_minutes(now, metric.updated)
        for metric in metrics.values()
        if metric.updated is not None
    ]
    if flare_metric and flare_metric.updated is not None:
        ages.append(age_minutes(now, flare_metric.updated))
    stale_minutes = math.inf if not ages else max(ages)
    if math.isinf(stale_minutes):
        stale_out = None
    elif stale_minutes < 0.5:
        stale_out = 0
    else:
        stale_out = int(round(stale_minutes))

    payload = {
        "updated": iso_z(now),
        "ttl_seconds": 600,
        "stale_minutes": stale_out,
        "sources": [{"id": key, "url": url} for key, url in SOURCES.items()],
        "now": {
            "sfi": metrics["sfi"].data,
            "k_index": metrics["kp"].data,
            "a_index": metrics["kp"].data.get("ap"),
            "mid_latitude_k_index": metrics["mid_k"].data,
            "xray": metrics["xray"].data,
            "solar_wind": metrics["solar_wind"].data,
            "sunspot": metrics["sunspot"].data,
        },
    }

    noise_planetary = estimate_noise(metrics["kp"].data.get("value"))
    noise_mid = estimate_noise(metrics["mid_k"].data.get("value"))
    if noise_planetary or noise_mid:
        payload["now"]["noise"] = {}
        if noise_planetary:
            payload["now"]["noise"]["planetary"] = {
                "s_units": noise_planetary["s_units"],
                "description": noise_planetary["description"],
                "k_value": metrics["kp"].data.get("value"),
            }
        if noise_mid:
            payload["now"]["noise"]["mid_latitude"] = {
                "s_units": noise_mid["s_units"],
                "description": noise_mid["description"],
                "k_value": metrics["mid_k"].data.get("value"),
            }

    diag = {}
    if errors:
        diag["errors"] = errors
    for key, metric in metrics.items():
        diag[f"{key}_updated"] = iso_z(metric.updated)
    if flare_metric:
        diag["flare_probs_updated"] = iso_z(flare_metric.updated)

    if flare_metric:
        forecast_block = payload.setdefault("forecast", {})
        forecast_block["flare_probability"] = flare_metric.data
    if three_day_forecast:
        payload.setdefault("forecast", {})["three_day"] = three_day_forecast
    if geomag_forecast:
        payload.setdefault("forecast", {})["geomagnetic_outlook"] = geomag_forecast
    if wwv_report:
        payload["wwv"] = wwv_report

    if diag:
        payload["diagnostics"] = diag
        if wwv_report:
            diag["wwv_issued"] = wwv_report.get("issued")
        if three_day_forecast and three_day_forecast.get("issued"):
            diag["three_day_issued"] = three_day_forecast.get("issued")
        if geomag_forecast and geomag_forecast.get("issued"):
            diag["geomag_issued"] = geomag_forecast.get("issued")

    return payload


def build_voice_summary(
    now: datetime,
    metrics: dict[str, Metric],
    flare_metric: Metric | None = None,
    wwv_report: dict[str, Any] | None = None,
    three_day_forecast: dict[str, Any] | None = None,
    geomag_forecast: dict[str, Any] | None = None,
) -> str:
    def format_time_words(dt: datetime) -> str:
        dt_utc = dt.astimezone(timezone.utc)
        hour_words = int_to_words(dt_utc.hour)
        if dt_utc.minute == 0:
            minute_words = "hundred"
        elif dt_utc.minute < 10:
            minute_words = f"oh {int_to_words(dt_utc.minute)}"
        else:
            minute_words = int_to_words(dt_utc.minute)
        return f"{hour_words} {minute_words} UTC"

    def time_phrase(metric: Metric) -> str | None:
        if not metric.updated:
            return None
        return format_time_words(metric.updated)

    def iso_time_phrase(iso_str: str | None) -> str | None:
        if not iso_str:
            return None
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        except ValueError:
            return None
        return format_time_words(dt)

    def format_date_for_voice(date_str: str, include_year: bool = False) -> str | None:
        try:
            dt = datetime.fromisoformat(date_str)
        except ValueError:
            return None
        month = dt.strftime("%B")
        day_words = ordinal_word(dt.day)
        if include_year:
            year_words = year_to_words(dt.year)
            return f"{month} {day_words}, {year_words}"
        return f"{month} {day_words}"

    def describe_band(energy: str | None) -> str:
        if not energy:
            return ""
        try:
            clean = energy.replace("nm", "").replace("–", "-")
            parts = [p.strip() for p in clean.split("-") if p.strip()]
            spoken_parts: list[str] = []
            for part in parts:
                digits = 0
                if "." in part:
                    digits = len(part.split(".")[1].rstrip("0")) or len(part.split(".")[1])
                spoken = decimal_to_words(part, digits)
                spoken_parts.append(spoken if spoken else part)
            if len(parts) == 2:
                return f"{spoken_parts[0]} to {spoken_parts[1]} nanometres"
            if len(parts) == 1:
                return f"{spoken_parts[0]} nanometres"
        except Exception:
            pass
        return f"{energy}"

    def percent_phrase(value: Any) -> str | None:
        words = format_int_words(value)
        if words is None:
            return None
        return f"{words} percent"

    def article_for(word: str) -> str:
        if not word:
            return "a"
        lowered = word.lower()
        if lowered.startswith(("one", "uni", "eu")):
            return "a"
        if lowered[0] in {"a", "e", "i", "o", "u"}:
            return "an"
        return "a"

    def spell_scale(code: str | None) -> str | None:
        if not code:
            return None
        code = code.strip()
        if len(code) == 2 and code[0].isalpha() and code[1].isdigit():
            return f"{code[0].upper()} {int_to_words(int(code[1]))}"
        return code

    def join_with_and(items: list[str]) -> str:
        filtered = [item for item in items if item]
        if not filtered:
            return ""
        if len(filtered) == 1:
            return filtered[0]
        if len(filtered) == 2:
            return f"{filtered[0]} and {filtered[1]}"
        return ", ".join(filtered[:-1]) + f", and {filtered[-1]}"

    def class_phrase(label: str | None) -> str | None:
        if not label:
            return None
        letter = label[0]
        remainder = label[1:]
        if not remainder:
            return letter
        try:
            digits = 0
            if "." in remainder:
                digits = len(remainder.split(".")[1])
            number_words = decimal_to_words(float(remainder), digits)
        except (ValueError, TypeError):
            return label
        if number_words:
            return f"{letter} {number_words}"
        return label
    sentences: list[str] = []

    # SFI
    sfi = metrics.get("sfi")
    sfi_data = sfi.data if sfi else {}
    sfi_value = format_decimal_words(sfi_data.get("value"), 0)
    sfi_mean = format_decimal_words(sfi_data.get("ninety_day_mean"), 0)
    sfi_schedule = sfi_data.get("schedule")
    if sfi_value:
        sentence = f"The Solar Flux Index is {sfi_value}."
        extra_bits = []
        if sfi_schedule:
            extra_bits.append(f"reported during the {sfi_schedule.lower()} reading")
        if sfi_mean:
            extra_bits.append(f"ninety-day mean {sfi_mean}")
        if extra_bits:
            sentence = sentence[:-1] + f" ({', '.join(extra_bits)})."
        sentences.append(sentence)
    else:
        sentences.append("The Solar Flux Index data is unavailable.")

    # Sunspot
    sunspot = metrics.get("sunspot")
    sunspot_data = sunspot.data if sunspot else {}
    sunspot_number = format_int_words(sunspot_data.get("number"))
    sunspot_area = format_int_words(sunspot_data.get("area_10e6"))
    sunspot_regions = _safe_int(sunspot_data.get("new_regions"))
    sunspot_date = sunspot_data.get("observation_date")
    if sunspot_number:
        parts = [f"The sunspot number is {sunspot_number}"]
        if sunspot_area:
            parts.append(f"covering roughly {sunspot_area} millionths of the solar hemisphere")
        if sunspot_regions is not None:
            if sunspot_regions == 0:
                parts.append("with no new regions observed")
            else:
                plural = "region" if sunspot_regions == 1 else "regions"
                region_words = format_int_words(sunspot_regions) or str(sunspot_regions)
                parts.append(f"with {region_words} new {plural} observed")
        if sunspot_date:
            try:
                date_dt = datetime.strptime(sunspot_date, "%Y-%m-%d")
                month_name = date_dt.strftime("%B")
                day_words = ordinal_word(date_dt.day)
                year_words = year_to_words(date_dt.year)
                date_phrase = f"{month_name} {day_words}, {year_words} based on UTC time"
            except ValueError:
                date_phrase = f"{sunspot_date} based on UTC time"
            parts.append(f"as of {date_phrase}")
        sentences.append(", ".join(parts) + ".")
    else:
        sentences.append("The sunspot number is unavailable.")

    # Planetary K/A
    kp_metric = metrics.get("kp")
    kp_data = kp_metric.data if kp_metric else {}
    kp_value = _safe_float(kp_data.get("value"))
    kp_desc = describe_kp_value(kp_value) if kp_value is not None else None
    kp_time = time_phrase(kp_metric) if kp_metric else None
    if kp_value is not None:
        kp_text = format_decimal_words(kp_value, 2)
        phrase = "The planetary K index"
        if kp_time:
            phrase += f" at {kp_time}"
        phrase += f" is {kp_text}"
        if kp_desc:
            phrase += f", indicating {kp_desc.lower()} conditions"
        phrase += "."
        sentences.append(phrase)
        ap_val = format_int_words(kp_data.get("ap"))
        if ap_val:
            sentences.append(f"The planetary A index is {ap_val}.")
        noise_planetary = estimate_noise(kp_value)
        if noise_planetary:
            s_units = noise_planetary["s_units"]
            description = noise_planetary["description"]
            if s_units:
                s_units_words = format_int_words(s_units) or str(s_units)
                sentences.append(
                    f"The planetary noise estimate measures at plus {s_units_words} S-units ({description})."
                )
            else:
                sentences.append("The planetary noise estimate measures at the baseline.")
        else:
            sentences.append("The planetary noise estimate is unavailable.")
    else:
        sentences.append("The planetary K index data is unavailable.")
        sentences.append("The planetary noise estimate is unavailable.")

    # Mid-latitude K/A
    mid_metric = metrics.get("mid_k")
    mid_data = mid_metric.data if mid_metric else {}
    mid_value = _safe_float(mid_data.get("value"))
    mid_desc = describe_kp_value(mid_value) if mid_value is not None else None
    mid_time = time_phrase(mid_metric) if mid_metric else None
    if mid_value is not None:
        mid_text = format_decimal_words(mid_value, 2)
        phrase = "The mid-latitude Boulder K index"
        if mid_time:
            phrase += f" at {mid_time}"
        phrase += f" is {mid_text}"
        if mid_desc:
            phrase += f", indicating {mid_desc.lower()} conditions"
        phrase += "."
        sentences.append(phrase)
        mid_ap = format_int_words(mid_data.get("ap"))
        if mid_ap:
            sentences.append(f"The Boulder A index is {mid_ap}.")
        noise_mid = estimate_noise(mid_value)
        if noise_mid:
            s_units = noise_mid["s_units"]
            description = noise_mid["description"]
            if s_units:
                s_units_words = format_int_words(s_units) or str(s_units)
                sentences.append(
                    f"The Boulder noise estimate measures at plus {s_units_words} S-units ({description})."
                )
            else:
                sentences.append("The Boulder noise estimate measures at the baseline.")
        else:
            sentences.append("The Boulder noise estimate is unavailable.")
    else:
        sentences.append("The mid-latitude Boulder K index data is unavailable.")
        sentences.append("The Boulder noise estimate is unavailable.")

    if wwv_report:
        wwv_sentences: list[str] = []
        wwv_k = wwv_report.get("estimated_planetary_k_index") or {}
        wwv_k_value = format_decimal_words(wwv_k.get("value"), 2)
        wwv_k_time = iso_time_phrase(wwv_k.get("time_tag"))
        if wwv_k_value:
            phrase = "WWV reports the estimated planetary K index"
            if wwv_k_time:
                phrase += f" at {wwv_k_time}"
            phrase += f" is {wwv_k_value}."
            wwv_sentences.append(phrase)
        wwv_a_value = format_int_words(wwv_report.get("estimated_planetary_a_index"))
        if wwv_a_value:
            wwv_sentences.append(f"The WWV estimated planetary A index is {wwv_a_value}.")
        wwv_flux = format_int_words(wwv_report.get("solar_flux"))
        if wwv_flux:
            wwv_sentences.append(f"WWV lists solar flux at {wwv_flux}.")
        space_weather = wwv_report.get("space_weather", {})
        if space_weather.get("past"):
            wwv_sentences.append(f"WWV reports the past day was {space_weather['past'].lower()}.")
        if space_weather.get("next"):
            wwv_sentences.append(f"WWV forecasts the next day to be {space_weather['next'].lower()}.")
        radio_info = wwv_report.get("radio_blackouts", {})
        past_radio = radio_info.get("past")
        if past_radio:
            level = past_radio.get("level")
            status = past_radio.get("status")
            if level and status:
                level_phrase = f"{level}-level"
                if status in {"occurred", "observed"}:
                    wwv_sentences.append(f"WWV observed {level_phrase} radio blackouts.")
                else:
                    wwv_sentences.append(f"WWV noted {level_phrase} radio blackouts {status}.")
        future_radio = radio_info.get("next")
        if future_radio:
            level = future_radio.get("level")
            status = future_radio.get("status")
            if level and status:
                level_phrase = f"{level}-level"
                if status == "likely":
                    wwv_sentences.append(f"WWV expects {level_phrase} radio blackouts are likely.")
                elif status == "expected":
                    wwv_sentences.append(f"WWV expects {level_phrase} radio blackouts.")
                else:
                    wwv_sentences.append(f"WWV expects {level_phrase} radio blackouts {status}.")
        sentences.extend(wwv_sentences)

    # Solar wind
    wind_metric = metrics.get("solar_wind")
    wind_data = wind_metric.data if wind_metric else {}
    wind_speed = format_decimal_words(wind_data.get("speed_kms"), 0)
    wind_density = format_decimal_words(wind_data.get("density"), 3)
    wind_temp = format_int_words(wind_data.get("temperature"))
    spacecraft = wind_data.get("spacecraft")
    if wind_speed or wind_density or wind_temp:
        if wind_speed:
            sentence = f"The solar wind speed is {wind_speed} kilometers per second"
        else:
            sentence = "The solar wind speed is unavailable"
        tail_parts: list[tuple[str, str]] = []
        if wind_density:
            tail_parts.append(("with", f"solar density measuring {wind_density} particles per cubic centimeter"))
        if wind_temp:
            connector = "and" if tail_parts else "with"
            tail_parts.append((connector, f"temperature at {wind_temp} Kelvin"))
        if tail_parts:
            sentence += " " + " ".join(f"{conn} {text}" for conn, text in tail_parts)
        if spacecraft:
            sentence += f" according to {spacecraft}"
        sentences.append(sentence + ".")
    else:
        sentences.append("The solar wind measurements are unavailable.")

    # X-ray
    xray_metric = metrics.get("xray")
    xray_data = xray_metric.data if xray_metric else {}
    primary_flux = format_scientific_words(xray_data.get("flux_wm2"))
    primary_energy = describe_band(xray_data.get("energy"))
    primary_class = class_phrase(xray_data.get("classification"))
    primary_sat = xray_data.get("satellite")
    secondary = xray_data.get("secondary") or {}
    secondary_flux = format_scientific_words(secondary.get("flux_wm2"))
    secondary_energy = describe_band(secondary.get("energy")) if secondary else ""
    if primary_flux:
        sentence = "The X-ray flux "
        if primary_energy:
            sentence += f"on the {primary_energy} band "
        sentence += f"is {primary_flux} watts per square metre"
        if primary_class:
            sentence += f", class {primary_class}"
        if primary_sat:
            sentence += f" from GOES-{primary_sat}"
        sentences.append(sentence + ".")
    else:
        sentences.append("The X-ray flux data is unavailable.")
    if secondary_flux:
        if secondary_energy:
            sentence = f"On the {secondary_energy} band the flux is {secondary_flux} watts per square metre"
        else:
            sentence = f"Additional X-ray flux is {secondary_flux} watts per square metre"
        secondary_class = class_phrase(secondary.get("classification"))
        if secondary_class:
            sentence += f", class {secondary_class}"
        sentences.append(sentence + ".")

    # Flare outlook
    flare_data = flare_metric.data if (flare_metric and flare_metric.data) else {}
    day1_c = percent_phrase(flare_data.get("c_class", {}).get("day1"))
    day1_m = percent_phrase(flare_data.get("m_class", {}).get("day1"))
    day1_x = percent_phrase(flare_data.get("x_class", {}).get("day1"))
    proton1 = percent_phrase(flare_data.get("proton_10mev", {}).get("day1"))
    polar = flare_data.get("polar_cap_absorption")
    if day1_c or day1_m or day1_x:
        sentences.append("Here is the twenty-four hour flare outlook.")
        chance_phrases: list[str] = []
        if day1_c:
            chance_phrases.append(f"{article_for(day1_c)} {day1_c} chance of a C-class flare")
        if day1_m:
            chance_phrases.append(f"{article_for(day1_m)} {day1_m} chance of an M-class flare")
        if day1_x:
            chance_phrases.append(f"{article_for(day1_x)} {day1_x} chance of an X-class flare")
        if chance_phrases:
            if len(chance_phrases) == 1:
                sentences.append(f"There is {chance_phrases[0]}.")
            else:
                clauses = [f"there is {phrase}" for phrase in chance_phrases]
                combined = ", ".join(clauses[:-1]) + f", and {clauses[-1]}"
                combined = combined[0].upper() + combined[1:]
                sentences.append(combined + ".")
    else:
        sentences.append("The flare probability data is unavailable.")
    if proton1:
        sentences.append(f"The ten mega-electron-volt proton event probability is {proton1}.")
    if polar:
        sentences.append(f"The polar cap absorption is {polar}.")

    if three_day_forecast:
        geomag_outlook = three_day_forecast.get("geomagnetic", {})
        if geomag_outlook.get("max_expected_kp") is not None:
            kp_words = format_decimal_words(geomag_outlook["max_expected_kp"], 2)
            scale_words = spell_scale(geomag_outlook.get("max_expected_scale"))
            if kp_words:
                if scale_words:
                    sentences.append(
                        f"NOAA expects maximum three-hour Kp to reach {kp_words}, {scale_words}, during the outlook window."
                    )
                else:
                    sentences.append(f"NOAA expects maximum three-hour Kp to reach {kp_words} during the outlook window.")
        if geomag_outlook.get("rationale"):
            sentences.append(geomag_outlook["rationale"])

        radio_outlook = three_day_forecast.get("radio_blackout", {})
        radio_days = radio_outlook.get("days") or []
        if radio_days:
            r1_values = [entry.get("R1-R2") for entry in radio_days if entry.get("R1-R2") is not None]
            r3_values = [entry.get("R3 or greater") for entry in radio_days if entry.get("R3 or greater") is not None]
            if r1_values and len(set(r1_values)) == 1 and (not r3_values or len(set(r3_values)) == 1):
                r1_phrase = percent_phrase(r1_values[0]) if r1_values else None
                clauses: list[str] = []
                if r1_phrase:
                    clauses.append(f"{article_for(r1_phrase)} {r1_phrase} chance of R1 to R2 radio blackouts")
                if r3_values:
                    r3_phrase = percent_phrase(r3_values[0])
                    if r3_phrase:
                        clauses.append(f"{article_for(r3_phrase)} {r3_phrase} chance of R3 or greater")
                if clauses:
                    end_phrase = format_date_for_voice(radio_days[-1]["date"]) or "the outlook period"
                    sentences.append(f"Radio blackout outlook: {' and '.join(clauses)} each day through {end_phrase}.")
            else:
                for entry in radio_days:
                    day_phrase = format_date_for_voice(entry["date"])
                    if not day_phrase:
                        continue
                    clauses = []
                    r1_value = entry.get("R1-R2")
                    if r1_value is not None:
                        r1_phrase = percent_phrase(r1_value)
                        if r1_phrase:
                            clauses.append(f"{article_for(r1_phrase)} {r1_phrase} chance of R1 to R2 events")
                    r3_value = entry.get("R3 or greater")
                    if r3_value is not None:
                        r3_phrase = percent_phrase(r3_value)
                        if r3_phrase:
                            clauses.append(f"{article_for(r3_phrase)} {r3_phrase} chance of R3 or greater")
                    if clauses:
                        sentences.append(f"For {day_phrase}, there is {' and '.join(clauses)}.")
        if radio_outlook.get("rationale"):
            sentences.append(radio_outlook["rationale"])

        solar_radiation = three_day_forecast.get("solar_radiation", {})
        probabilities = solar_radiation.get("probabilities") or []
        for row in probabilities:
            if row["label"].lower().startswith("s1"):
                values = row.get("values") or []
                percent_entries: list[tuple[str, str]] = []
                for item in values:
                    percent_text = percent_phrase(item["percent"])
                    if percent_text:
                        percent_entries.append((item["date"], percent_text))
                if percent_entries:
                    percent_texts = [entry[1] for entry in percent_entries]
                    if len(set(percent_texts)) == 1:
                        sentences.append(
                            f"Solar radiation storm outlook: {article_for(percent_texts[0])} {percent_texts[0]} chance of S1 or greater through the period."
                        )
                    else:
                        for date_value, percent_text in percent_entries:
                            day_phrase = format_date_for_voice(date_value)
                            if day_phrase and percent_text:
                                sentences.append(
                                    f"For {day_phrase}, there is {article_for(percent_text)} {percent_text} chance of an S1 solar radiation storm."
                                )
        if solar_radiation.get("rationale"):
            sentences.append(solar_radiation["rationale"])

    if geomag_forecast:
        ap_section = geomag_forecast.get("ap") or {}
        predicted = ap_section.get("predicted") or []
        if predicted:
            value_words: list[str] = []
            for item in predicted:
                words = format_int_words(item["value"])
                if words:
                    value_words.append(words)
            if value_words:
                start_phrase = format_date_for_voice(predicted[0]["date"]) or "the outlook period"
                end_phrase = format_date_for_voice(predicted[-1]["date"]) or "the outlook period"
                sentences.append(
                    "Predicted Ap values are "
                    + join_with_and(value_words)
                    + f" from {start_phrase} through {end_phrase}."
                )

    return "\n".join(sentences).strip()


# --- CLI -----------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/solar.json"),
        help="Output file path (default: data/solar.json)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON with indentation.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds (default: 10).",
    )
    parser.add_argument(
        "--voice-output",
        type=Path,
        help="Write spoken summary to this path (default: alongside JSON output).",
    )
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Do not write the spoken summary file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    t_start = time.perf_counter()
    now = utcnow()
    errors: list[str] = []

    if args.no_voice:
        voice_output: Path | None = None
    else:
        if args.voice_output:
            voice_output = args.voice_output
        else:
            voice_output = args.output.with_name(f"{args.output.stem}_voice.txt")

    # Fetch all sources (serial to avoid hammering SWPC; still fast).
    raw_data: dict[str, Any] = {}
    for key, url in SOURCES.items():
        try:
            if key in TEXT_SOURCES:
                raw_data[key] = fetch_text(url, timeout=args.timeout)
            else:
                raw_data[key] = fetch_json(url, timeout=args.timeout)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{key}: {exc}")
            raw_data[key] = "" if key in TEXT_SOURCES else []

    metrics = {
        "sfi": extract_sfi(raw_data.get("f10_7", [])),
        "kp": extract_kp(raw_data.get("kp", []), "SWPC planetary_k_index_1m.json"),
        "mid_k": extract_kp(raw_data.get("boulder_k", []), "SWPC boulder_k_index_1m.json"),
        "solar_wind": extract_solar_wind(raw_data.get("solar_wind", [])),
        "xray": extract_xray(raw_data.get("xray", [])),
        "sunspot": extract_sunspot(raw_data.get("sunspot", "")),
    }

    flare_metric = extract_flare_probabilities(raw_data.get("flare_probs", []))
    wwv_report = parse_wwv(raw_data.get("wwv", ""), now.year)
    three_day = parse_three_day_forecast(raw_data.get("three_day", ""), now.year)
    geomag = parse_geomag_forecast(raw_data.get("geomag_forecast", ""), now.year)

    payload = build_payload(now, metrics, errors, flare_metric, wwv_report, three_day, geomag)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    indent = 2 if args.pretty or args.output.suffix == ".json" else None
    with args.output.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=indent)
        fh.write("\n")

    if voice_output:
        voice_output.parent.mkdir(parents=True, exist_ok=True)
        voice_text = build_voice_summary(now, metrics, flare_metric, wwv_report, three_day, geomag)
        with voice_output.open("w", encoding="utf-8") as fh:
            fh.write(voice_text + "\n")
        print(f"[solar] wrote {voice_output}")

    duration_ms = int((time.perf_counter() - t_start) * 1000)
    print(f"[solar] wrote {args.output} in {duration_ms} ms (errors={len(errors)})")
    if errors:
        for err in errors:
            print(f"[solar] WARN: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
