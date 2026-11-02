"""DEMONSTRATION crowd history generator.

There is no verified public source of hourly visitor counts for Indian attractions, so this module
plays the role of "ticket gates and footfall sensors". It produces plausible, deterministic hourly
counts from each attraction's ASSUMED carrying capacity and popularity, the category's daily rhythm,
weekday, season, national holidays and simulated rain.

To use real data, replace `counts()` with a loader that returns the same columns
(key, date, hour, count, rain) from gate or sensor records, then retrain (scripts/train_model.py).
"""
from __future__ import annotations

import datetime as dt
import math
import zlib

import numpy as np
import pandas as pd

from ..data.catalog import HOLIDAYS

HOLIDAY_DATES = {dt.date(*k): v for k, v in HOLIDAYS.items()}

# Hourly rhythm per category: mixture of Gaussians (mean hour, sd, weight)
PROFILES = {
    "beach": [(7.0, 1.5, 0.5), (17.5, 1.8, 1.0)],
    "heritage": [(11.0, 2.0, 1.0), (16.0, 1.8, 0.8)],
    "spiritual": [(7.0, 1.5, 0.8), (18.5, 1.8, 1.0)],
    "museum": [(12.5, 2.5, 1.0)],
    "waterfall": [(14.5, 2.5, 1.0)],
    "lake": [(11.5, 2.5, 1.0), (16.5, 1.5, 0.8)],
    "viewpoint": [(17.0, 1.6, 1.0), (8.0, 1.5, 0.5)],
    "garden": [(11.0, 2.2, 0.8), (16.5, 2.0, 1.0)],
    "wildlife": [(7.5, 1.5, 1.0), (15.5, 1.5, 0.8)],
    "market": [(18.0, 2.5, 1.0)],
    "adventure": [(12.0, 2.5, 1.0)],
    "nature": [(11.5, 2.5, 1.0)],
    "plantation": [(10.5, 2.0, 1.0), (15.0, 2.0, 0.55)],
    "river": [(6.5, 1.2, 0.9), (18.5, 1.3, 1.0)],
}
DEFAULT_PROFILE = [(13.0, 3.0, 1.0)]
DOW_MULT = np.array([0.55, 0.50, 0.50, 0.55, 0.70, 1.00, 0.92])  # Mon..Sun
OFF_SEASON = 0.55
RAIN_MULT = {"museum": 1.3, "market": 1.05, "spiritual": 0.85, "beach": 0.3, "waterfall": 0.7, "lake": 0.35,
             "viewpoint": 0.5, "river": 0.5}
RAIN_DEFAULT = 0.6
# probability that a given afternoon hour is rainy, by climate and month (index 1..12)
_MONSOON = {6: 1.0, 7: 1.0, 8: 1.0, 9: 0.8, 10: 0.35, 11: 0.2, 5: 0.25}
_CLIMATE_RAIN = {"coastal": 0.45, "mountain": 0.5, "plains": 0.35, "desert": 0.1, "tropical": 0.45}


def holiday(d: dt.date) -> dict:
    e = HOLIDAY_DATES.get(d)
    return {"holiday": e is not None, "name": e[0] if e else None, "festival": bool(e and e[1])}


def in_season(spec: dict, month: int) -> bool:
    return not spec.get("best_months") or month in spec["best_months"]


def rain_probability(climate: str, month: int, hour: int) -> float:
    base = _CLIMATE_RAIN.get(climate, 0.35) * _MONSOON.get(month, 0.08)
    return base * (1.0 if 12 <= hour <= 19 else 0.5)


def hours_for(spec: dict) -> range:
    """Hours modelled for an attraction: its opening hours, bounded to 5 AM–11 PM."""
    return range(max(spec["open_hour"], 5), min(spec["close_hour"], 23))


def _profile(category: str, hours: np.ndarray, open_h: int, close_h: int) -> np.ndarray:
    comp = PROFILES.get(category, DEFAULT_PROFILE)
    hc = hours + 0.5

    def raw(x):
        return sum(w * np.exp(-0.5 * ((x - m) / s) ** 2) for m, s, w in comp)

    span = np.arange(max(open_h, 5), min(close_h, 23)) + 0.5
    return raw(hc) / max(raw(span).max(), 1e-6)


def _rng(*parts) -> np.random.Generator:
    return np.random.default_rng(zlib.crc32("|".join(map(str, parts)).encode()))


def simulated_rain(climate: str, d: dt.date, hours: np.ndarray) -> np.ndarray:
    r = _rng("rain", climate, d.isoformat())
    wet_day = r.random() < min(1.0, rain_probability(climate, d.month, 15) * 1.6)
    if not wet_day:
        return np.zeros(len(hours))
    start = int(r.integers(11, 17))
    dur = int(r.integers(2, 6))
    return ((hours >= start) & (hours < start + dur)).astype(float)


def counts(specs: list[dict], dates: list[dt.date]) -> pd.DataFrame:
    """Hourly demonstration visitor counts for each attraction spec and date (open hours only)."""
    frames = []
    for s in specs:
        hours = np.array(list(hours_for(s)))
        if not len(hours):
            continue
        prof = _profile(s["category"], hours, s["open_hour"], s["close_hour"])
        rain_m = RAIN_MULT.get(s["category"], RAIN_DEFAULT)
        for d in dates:
            cal = holiday(d)
            mult = DOW_MULT[d.weekday()]
            if cal["holiday"]:
                mult = max(mult, 0.95) * 1.25
            if cal["festival"]:
                mult *= 1.4 if s["category"] == "spiritual" else 1.1
            if not in_season(s, d.month):
                mult *= OFF_SEASON
            rain = simulated_rain(s.get("climate", "plains"), d, hours)
            wm = np.where(rain > 0, 1.0 if s.get("covered") else rain_m, 1.0)
            noise = np.exp(_rng(s["key"], d.isoformat()).normal(0, 0.10, len(hours)))
            c = s["capacity"] * s["popularity"] * prof * mult * wm * noise
            c = np.clip(c, 0, 1.6 * s["capacity"])
            frames.append(pd.DataFrame({"key": s["key"], "date": d, "hour": hours, "count": c, "rain": rain}))
    if not frames:
        return pd.DataFrame(columns=["key", "date", "hour", "count", "rain"])
    return pd.concat(frames, ignore_index=True)


def date_range(end_date: dt.date, days: int) -> list[dt.date]:
    return [end_date - dt.timedelta(days=i) for i in range(days, 0, -1)]


def expected_rain(climate: str, d: dt.date, hour: int) -> float:
    """Rain feature when no live forecast is available: climatological probability."""
    return round(rain_probability(climate, d.month, hour), 3)


def describe_month(month: int) -> str:
    return dt.date(2026, month, 1).strftime("%B")


__all__ = ["counts", "holiday", "in_season", "hours_for", "expected_rain", "date_range", "math"]
