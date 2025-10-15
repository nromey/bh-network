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
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
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


# --- Assembly ------------------------------------------------------------------

def build_payload(
    now: datetime,
    metrics: dict[str, Metric],
    errors: list[str],
    flare_metric: Metric | None = None,
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
        payload["forecast"] = {
            "flare_probability": flare_metric.data,
        }

    if diag:
        payload["diagnostics"] = diag

    return payload


def build_voice_summary(
    now: datetime,
    metrics: dict[str, Metric],
    flare_metric: Metric | None = None,
) -> str:
    def time_phrase(metric: Metric) -> str | None:
        if not metric.updated:
            return None
        dt = metric.updated.astimezone(timezone.utc)
        return dt.strftime("%H:%M UTC")

    def describe_band(energy: str | None) -> str:
        if not energy:
            return ""
        try:
            clean = energy.replace("nm", "").replace("–", "-")
            parts = [p.strip() for p in clean.split("-") if p.strip()]
            if len(parts) == 2:
                return f"{parts[0]} to {parts[1]} nanometres"
            if len(parts) == 1:
                return f"{parts[0]} nanometres"
        except Exception:
            pass
        return f"{energy}"

    def percent_phrase(value: Any) -> str | None:
        iv = _safe_int(value)
        if iv is None:
            return None
        return f"{iv} percent"

    sentences: list[str] = []

    # SFI
    sfi = metrics.get("sfi")
    sfi_data = sfi.data if sfi else {}
    sfi_value = format_decimal(sfi_data.get("value"), 0)
    sfi_mean = format_decimal(sfi_data.get("ninety_day_mean"), 0)
    sfi_schedule = sfi_data.get("schedule")
    if sfi_value:
        sentence = f"The Solar Flux Index is {sfi_value}."
        extra_bits = []
        if sfi_schedule:
            extra_bits.append(f"reported during the {sfi_schedule.lower()} reading")
        if sfi_mean:
            extra_bits.append(f"90-day mean {sfi_mean}")
        if extra_bits:
            sentence = sentence[:-1] + f" ({', '.join(extra_bits)})."
        sentences.append(sentence)
    else:
        sentences.append("Solar Flux Index data is unavailable.")

    # Sunspot
    sunspot = metrics.get("sunspot")
    sunspot_data = sunspot.data if sunspot else {}
    sunspot_number = format_int(sunspot_data.get("number"))
    sunspot_area = format_int(sunspot_data.get("area_10e6"))
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
                parts.append(f"with {sunspot_regions} new {plural} observed")
        if sunspot_date:
            try:
                date_str = datetime.strptime(sunspot_date, "%Y-%m-%d").strftime("%d %B %Y")
            except ValueError:
                date_str = sunspot_date
            parts.append(f"as of {date_str} UTC")
        sentences.append(", ".join(parts) + ".")
    else:
        sentences.append("Sunspot number is unavailable.")

    # Planetary K/A
    kp_metric = metrics.get("kp")
    kp_data = kp_metric.data if kp_metric else {}
    kp_value = _safe_float(kp_data.get("value"))
    kp_desc = describe_kp_value(kp_value) if kp_value is not None else None
    kp_time = time_phrase(kp_metric) if kp_metric else None
    if kp_value is not None:
        kp_text = format_decimal(kp_value, 2)
        phrase = "The planetary K index"
        if kp_time:
            phrase += f" at {kp_time}"
        phrase += f" is {kp_text}"
        if kp_desc:
            phrase += f", indicating {kp_desc.lower()} conditions"
        phrase += "."
        sentences.append(phrase)
        ap_val = format_int(kp_data.get("ap"))
        if ap_val:
            sentences.append(f"The planetary A index is {ap_val}.")
        noise_planetary = estimate_noise(kp_value)
        if noise_planetary:
            if noise_planetary["s_units"]:
                sentences.append(
                    f"Planetary noise estimate around plus {noise_planetary['s_units']} S-units ({noise_planetary['description']})."
                )
            else:
                sentences.append(f"Planetary noise estimate: {noise_planetary['description']}.")
    else:
        sentences.append("Planetary K index data is unavailable.")

    # Mid-latitude K/A
    mid_metric = metrics.get("mid_k")
    mid_data = mid_metric.data if mid_metric else {}
    mid_value = _safe_float(mid_data.get("value"))
    mid_desc = describe_kp_value(mid_value) if mid_value is not None else None
    mid_time = time_phrase(mid_metric) if mid_metric else None
    if mid_value is not None:
        mid_text = format_decimal(mid_value, 2)
        phrase = "The mid-latitude Boulder K index"
        if mid_time:
            phrase += f" at {mid_time}"
        phrase += f" is {mid_text}"
        if mid_desc:
            phrase += f", indicating {mid_desc.lower()} conditions"
        phrase += "."
        sentences.append(phrase)
        mid_ap = format_int(mid_data.get("ap"))
        if mid_ap:
            sentences.append(f"The Boulder A index is {mid_ap}.")
        noise_mid = estimate_noise(mid_value)
        if noise_mid:
            if noise_mid["s_units"]:
                sentences.append(
                    f"Boulder noise estimate around plus {noise_mid['s_units']} S-units ({noise_mid['description']})."
                )
            else:
                sentences.append(f"Boulder noise estimate: {noise_mid['description']}.")
    else:
        sentences.append("Mid-latitude Boulder K index data is unavailable.")

    # Solar wind
    wind_metric = metrics.get("solar_wind")
    wind_data = wind_metric.data if wind_metric else {}
    wind_speed = format_decimal(wind_data.get("speed_kms"), 0)
    wind_density = format_decimal(wind_data.get("density"), 3)
    wind_temp = format_int(wind_data.get("temperature"))
    spacecraft = wind_data.get("spacecraft")
    if wind_speed or wind_density or wind_temp:
        parts = []
        if wind_speed:
            parts.append(f"speed {wind_speed} kilometers per second")
        if wind_density:
            parts.append(f"density {wind_density} particles per cubic centimeter")
        if wind_temp:
            parts.append(f"temperature {wind_temp} Kelvin")
        sentence = "Solar wind " + ", ".join(parts)
        if spacecraft:
            sentence += f" according to {spacecraft}"
        sentences.append(sentence + ".")
    else:
        sentences.append("Solar wind measurements are unavailable.")

    # X-ray
    xray_metric = metrics.get("xray")
    xray_data = xray_metric.data if xray_metric else {}
    primary_flux = format_scientific(xray_data.get("flux_wm2"))
    primary_energy = describe_band(xray_data.get("energy"))
    primary_class = xray_data.get("classification")
    primary_sat = xray_data.get("satellite")
    secondary = xray_data.get("secondary") or {}
    secondary_flux = format_scientific(secondary.get("flux_wm2"))
    secondary_energy = describe_band(secondary.get("energy")) if secondary else ""
    if primary_flux:
        sentence = "X-ray flux "
        if primary_energy:
            sentence += f"on the {primary_energy} band "
        sentence += f"is {primary_flux} watts per square metre"
        if primary_class:
            sentence += f", class {primary_class}"
        if primary_sat:
            sentence += f" from GOES-{primary_sat}"
        sentences.append(sentence + ".")
    else:
        sentences.append("X-ray flux data is unavailable.")
    if secondary_flux:
        if secondary_energy:
            sentence = f"On the {secondary_energy} band the flux is {secondary_flux} watts per square metre"
        else:
            sentence = f"Additional X-ray flux is {secondary_flux} watts per square metre"
        secondary_class = secondary.get("classification")
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
        probs = []
        if day1_c:
            probs.append(f"C-class {day1_c}")
        if day1_m:
            probs.append(f"M-class {day1_m}")
        if day1_x:
            probs.append(f"X-class {day1_x}")
        sentence = "Here is the 24 hour flare outlook: " + ", ".join(probs)
        sentences.append(sentence + ".")
    else:
        sentences.append("Flare probability data is unavailable.")
    if proton1:
        sentences.append(f"The 10 mega-electron-volt proton event probability is {proton1}.")
    if polar:
        sentences.append(f"Polar cap absorption level is {polar}.")

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
            if key == "sunspot":
                raw_data[key] = fetch_text(url, timeout=args.timeout)
            else:
                raw_data[key] = fetch_json(url, timeout=args.timeout)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{key}: {exc}")
            raw_data[key] = "" if key == "sunspot" else []

    metrics = {
        "sfi": extract_sfi(raw_data.get("f10_7", [])),
        "kp": extract_kp(raw_data.get("kp", []), "SWPC planetary_k_index_1m.json"),
        "mid_k": extract_kp(raw_data.get("boulder_k", []), "SWPC boulder_k_index_1m.json"),
        "solar_wind": extract_solar_wind(raw_data.get("solar_wind", [])),
        "xray": extract_xray(raw_data.get("xray", [])),
        "sunspot": extract_sunspot(raw_data.get("sunspot", "")),
    }

    flare_metric = extract_flare_probabilities(raw_data.get("flare_probs", []))

    payload = build_payload(now, metrics, errors, flare_metric)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    indent = 2 if args.pretty or args.output.suffix == ".json" else None
    with args.output.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=indent)
        fh.write("\n")

    if voice_output:
        voice_output.parent.mkdir(parents=True, exist_ok=True)
        voice_text = build_voice_summary(now, metrics, flare_metric)
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
