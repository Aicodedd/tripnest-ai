"""Destination-level crowd prediction: aggregates the per-attraction model forecasts into one answer."""
from __future__ import annotations

import datetime as dt

from ..models import Destination
from . import crowd, crowd_sim, runtime

BAND_CONFIDENCE = 0.8
LIMITATIONS = [
    "No live crowd counts are used. The history the model learned from is simulated demonstration data, not recorded visitor counts.",
    "Carrying capacities are assumptions, not official limits, so levels show relative crowding, not exact safety limits.",
    "Weather, local events and closures on the day are not known to the model beyond typical season, weekday and holiday patterns.",
    "The likely range adds each attraction's 80% range, so it is wider than a true destination-level range.",
]


def hour_label(h: int) -> str:
    return f"{h % 12 or 12} {'AM' if h < 12 or h == 24 else 'PM'}"


SLOTS = [("early", "Early morning", 5, 8, "5–8 AM"), ("morning", "Morning", 8, 12, "8 AM–12 PM"),
         ("afternoon", "Afternoon", 12, 16, "12–4 PM"), ("evening", "Evening", 16, 20, "4–8 PM")]
SLOT_KEYS = ["all"] + [s[0] for s in SLOTS]
QUIET_BELOW = 0.70  # a "best time" is only recommended if its predicted crowd stays below the High threshold


def hm(h: int) -> str:
    return f"{h % 12 or 12}:00 {'AM' if h < 12 or h == 24 else 'PM'}"


def slot_hours(key: str) -> tuple[int, int]:
    """Hours [start, end) covered by a slot; 'all' is the whole day from 5 AM to 8 PM."""
    if key == "all":
        return 5, 20
    s = next(x for x in SLOTS if x[0] == key)
    return s[2], s[3]


def slot_peak(hourly: list[dict], key: str) -> dict | None:
    a, b = slot_hours(key)
    rng = [h for h in hourly if a <= h["hour"] < b]
    return max(rng, key=lambda h: h["util"]) if rng else None


def timeline(hourly: list[dict]) -> list[dict]:
    """Four time-of-day slots with the busiest predicted level in each; the calmest available slot is flagged."""
    out = []
    for key, label, a, b, rng_label in SLOTS:
        rng = [h for h in hourly if a <= h["hour"] < b]
        if not rng:
            out.append({"key": key, "label": label, "range": rng_label, "available": False, "level": "Closed", "util": 0.0,
                        "visitors": 0, "avg_util": None, "best": False})
            continue
        pk = max(rng, key=lambda h: h["util"])
        out.append({"key": key, "label": label, "range": rng_label, "available": True, "level": pk["level"], "util": pk["util"],
                    "visitors": pk["visitors"], "avg_util": round(sum(h["util"] for h in rng) / len(rng), 3), "best": False})
    avail = [s for s in out if s["available"]]
    if len(avail) >= 1:
        min(avail, key=lambda s: s["avg_util"])["best"] = True
    return out


def best_window(hourly: list[dict]) -> dict:
    """The calmest hour (5 AM to 8 PM). Not recommended when the data cannot support it."""
    rng = [h for h in hourly if 5 <= h["hour"] <= 19]
    if len(rng) < 3:
        return {"available": False, "message": "Not enough opening hours on this date to recommend a time."}
    q = min(rng, key=lambda h: h["util"])
    if q["util"] >= QUIET_BELOW:
        return {"available": False, "message": "Crowds are predicted to stay high through the day on this date. Try another date."}
    return {"available": True, "start_hour": q["hour"], "end_hour": q["hour"] + 1, "label": f"{hm(q['hour'])} – {hm(q['hour'] + 1)}",
            "level": q["level"], "util": q["util"], "visitors": q["visitors"],
            "message": "Lower crowd levels are predicted during this period."}


def aggregate_day(d: Destination, day: dt.date) -> list[dict]:
    """Hourly destination view: visitors, range and utilisation summed over the attractions open that hour."""
    by_hour: dict[int, dict] = {}
    for a in d.attractions:
        for h in runtime.day_forecast(runtime.spec(a), day):
            x = by_hour.setdefault(h["hour"], {"visitors": 0, "low": 0, "high": 0, "cap": 0})
            x["visitors"] += h["visitors"]
            x["low"] += h["low"]
            x["high"] += h["high"]
            x["cap"] += a.capacity
    out = []
    for hour in sorted(by_hour):
        x = by_hour[hour]
        util = x["visitors"] / x["cap"] if x["cap"] else 0.0
        out.append({"hour": hour, "label": hour_label(hour), "util": round(util, 3), "visitors": x["visitors"],
                    "low": x["low"], "high": x["high"], "level": crowd.level_of(util, False)})
    return out


def peak_in(hourly: list[dict], start: int, end: int) -> dict | None:
    rng = [h for h in hourly if start <= h["hour"] <= end]
    return max(rng, key=lambda h: h["util"]) if rng else None


def quietest(hourly: list[dict], start: int = 7, end: int = 19) -> dict | None:
    rng = [h for h in hourly if start <= h["hour"] <= end] or hourly
    return min(rng, key=lambda h: h["util"]) if rng else None


def card(hourly: list[dict], start: int = 9, end: int = 17) -> dict:
    """Crowd summary for a recommendation card: the busiest hour in the daytime window and the quietest hour."""
    pk = peak_in(hourly, start, end) or peak_in(hourly, 0, 24)
    q = quietest(hourly)
    if not pk or not q:
        return {"crowd": {"level": "Closed", "util": 0.0, "visitors": 0, "low": 0, "high": 0, "peak_hour": None, "peak_label": None},
                "suggested_time": {"hour": None, "label": "Not available", "level": "Closed", "util": 0.0}}
    return {"crowd": {"level": pk["level"], "util": pk["util"], "visitors": pk["visitors"], "low": pk["low"], "high": pk["high"],
                      "peak_hour": pk["hour"], "peak_label": pk["label"]},
            "suggested_time": {"hour": q["hour"], "label": q["label"], "level": q["level"], "util": q["util"]}}


def provenance() -> dict:
    p = runtime.provenance()
    info = runtime.model().info
    return {**p, "data_freshness": f"Model trained {info.get('trained_at', 'unknown')[:10]}; demonstration history simulated up to "
                                   f"{info.get('history_end', 'unknown')}. Forecasts are computed on request for the date you choose.",
            "limitations": LIMITATIONS,
            "uncertainty": {"method": "80% range from the model's error on a held-out test fortnight (log-normal residuals)",
                            "confidence": BAND_CONFIDENCE}}


def predict(d: Destination, day: dt.date, start: int, end: int) -> dict:
    runtime.prefetch_day([runtime.spec(a) for a in d.attractions], day)
    hourly = aggregate_day(d, day)
    pk = peak_in(hourly, start, end)
    rng = [h for h in hourly if start <= h["hour"] <= end]
    if pk:
        selected = {"from": start, "to": end, "level": pk["level"], "peak_hour": pk["hour"], "peak_label": pk["label"],
                    "visitors": pk["visitors"], "low": pk["low"], "high": pk["high"], "util": pk["util"],
                    "avg_util": round(sum(h["util"] for h in rng) / len(rng), 3)}
    else:
        selected = {"from": start, "to": end, "level": "Closed", "peak_hour": None, "peak_label": None, "visitors": 0,
                    "low": 0, "high": 0, "util": 0.0, "avg_util": 0.0}
    q = quietest(hourly)
    best = ({"hour": q["hour"], "label": q["label"], "level": q["level"], "util": q["util"], "visitors": q["visitors"]}
            if q else None)

    days = [day + dt.timedelta(days=i) for i in range(7)]
    specs = [runtime.spec(a) for a in d.attractions]
    for x in days:
        runtime.prefetch_day(specs, x)
    week = []
    for x in days:
        hx = aggregate_day(d, x)
        p, qq = peak_in(hx, 9, 17) or peak_in(hx, 0, 24), quietest(hx)
        week.append({"date": x.isoformat(), "weekday": x.strftime("%a"), "peak_level": p["level"] if p else "Closed",
                     "peak_util": p["util"] if p else 0.0, "peak_hour": p["hour"] if p else None,
                     "quietest_label": qq["label"] if qq else None, "quietest_level": qq["level"] if qq else "Closed"})

    attrs = []
    for a in d.attractions:
        fc = runtime.day_forecast(runtime.spec(a), day)
        apk = peak_in(fc, start, end)
        aq = quietest([{**h, "label": hour_label(h["hour"])} for h in fc])
        attrs.append({"slug": a.slug, "name": a.name, "category": a.category, "sensitive": a.sensitive, "capacity": a.capacity,
                      "open_hour": a.open_hour, "close_hour": a.close_hour,
                      "level": apk["level"] if apk else "Closed", "peak_label": hour_label(apk["hour"]) if apk else None,
                      "visitors": apk["visitors"] if apk else 0, "util": apk["util"] if apk else 0.0,
                      "best_hour_label": hour_label(aq["hour"]) if aq else "Not available", "best_level": aq["level"] if aq else "Closed"})
    attrs.sort(key=lambda x: -x["capacity"])

    return {"date": day.isoformat(), "selected": selected, "best_time": best, "hourly": hourly, "week": week, "attractions": attrs,
            "calendar": crowd_sim.holiday(day), "in_season": not d.best_months or day.month in d.best_months,
            "capacity": {"assumed": True, "note": "Carrying capacities are assumptions for the prototype, not official limits."},
            "timeline": timeline(hourly), "best_window": best_window(hourly), "provenance": provenance()}
