"""Crowd levels, forecasts, best times and live estimates built on the forecasting model."""
from __future__ import annotations

import datetime as dt
import math

from . import crowd_sim

LEVELS = ["Low", "Moderate", "High", "At Capacity"]
STANDARD_T = (0.40, 0.70, 0.90)   # fractions of carrying capacity
SENSITIVE_T = (0.25, 0.50, 0.70)  # stricter for ecologically sensitive sites
REPORT_VALUE = {"low": 0.30, "moderate": 0.55, "high": 0.80, "packed": 1.05}
BAND_Z = 1.2816  # 80% interval


def thresholds(sensitive: bool) -> tuple[float, float, float]:
    return SENSITIVE_T if sensitive else STANDARD_T


def level_of(util: float, sensitive: bool) -> str:
    lo, mid, hi = thresholds(sensitive)
    return "Low" if util < lo else "Moderate" if util < mid else "High" if util < hi else "At Capacity"


def p_exceed(util: float, sensitive: bool, sigma: float) -> float:
    """P(actual utilisation reaches the 'At Capacity' threshold), assuming log-normal forecast error."""
    thr = thresholds(sensitive)[2]
    z = (math.log(thr + 0.02) - math.log(util + 0.02)) / max(sigma, 1e-3)
    return 0.5 * math.erfc(z / math.sqrt(2))


def _rain(spec, d, h, rain_by_hour):
    if rain_by_hour is not None and (d, h) in rain_by_hour:
        return rain_by_hour[(d, h)]
    return crowd_sim.expected_rain(spec.get("climate", "plains"), d, h)


def day_rows(spec: dict, d: dt.date, rain_by_hour: dict | None = None) -> list[tuple]:
    """Model input rows for one attraction's day (open hours only)."""
    return [(spec, d, h, _rain(spec, d, h, rain_by_hour)) for h in crowd_sim.hours_for(spec)]


def day_forecast(model, spec: dict, d: dt.date, rain_by_hour: dict | None = None) -> list[dict]:
    rows = day_rows(spec, d, rain_by_hour)
    return shape_day(model, spec, [r[2] for r in rows], model.predict_util(rows))


def shape_day(model, spec: dict, hours: list[int], utils) -> list[dict]:
    """Turn predicted utilisation per hour into levels, visitor counts and an 80% band."""
    sig = model.sigma_for(spec["category"])
    out = []
    for h, u in zip(hours, utils):
        u = float(u)
        lo, hi = (u + 0.02) * math.exp(-BAND_Z * sig) - 0.02, (u + 0.02) * math.exp(BAND_Z * sig) - 0.02
        cap = spec["capacity"]
        out.append({"hour": h, "util": round(u, 3), "visitors": int(round(u * cap)),
                    "low": int(round(max(lo, 0) * cap)), "high": int(round(hi * cap)),
                    "level": level_of(u, spec["sensitive"]),
                    "p_exceed": round(p_exceed(u, spec["sensitive"], sig), 3)})
    return out


def peak(day: list[dict]) -> dict | None:
    return max(day, key=lambda h: h["util"]) if day else None


def best_times(model, spec: dict, start: dt.date, days: int = 7, n: int = 5, rain_by_hour=None) -> list[dict]:
    """Quietest visiting slots over the next `days`, at most two per day, between 7 AM and 8 PM."""
    hours = [h for h in crowd_sim.hours_for(spec) if 7 <= h <= 20]
    rows = [(spec, start + dt.timedelta(days=i), h) for i in range(days) for h in hours]
    utils = model.predict_util([(s, d, h, _rain(s, d, h, rain_by_hour)) for s, d, h in rows])
    cand = sorted(zip(utils, rows), key=lambda x: x[0])
    picked, per_day = [], {}
    for u, (_, d, h) in cand:
        if per_day.get(d, 0) >= 2:
            continue
        per_day[d] = per_day.get(d, 0) + 1
        picked.append({"date": d.isoformat(), "hour": h, "util": round(float(u), 3),
                       "level": level_of(float(u), spec["sensitive"])})
        if len(picked) == n:
            break
    return picked


def blend_reports(model_util: float, report_levels: list[str]) -> dict:
    """Combine the model estimate with recent traveller reports (more reports -> more weight, max 60%)."""
    n = len(report_levels)
    if not n:
        return {"util": model_util, "reports": 0}
    avg = sum(REPORT_VALUE.get(r, 0.55) for r in report_levels) / n
    w = min(0.6, 0.2 * n)
    return {"util": round((1 - w) * model_util + w * avg, 3), "reports": n}
