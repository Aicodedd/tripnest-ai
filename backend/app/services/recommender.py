"""Destination recommender. It consumes the crowd model's predictions; it does not use popularity.

score = Σ weight × factor, over the factors that apply to this request (weights are re-normalised to sum to 1):
    crowd     0.40  how quiet the destination is predicted to be on the chosen date (busiest daytime hour)
    interest  0.25  does it match the chosen interest (only when one is chosen)
    distance  0.20  nearer to the starting location (only when a start is given)
    season    0.15  is the travel month in the destination's best season
Every factor is 0..1, shown in `breakdown`, and turned into a plain-language reason.
"""
from __future__ import annotations

import datetime as dt
import math

from ..models import Destination
from . import prediction, runtime

BASE_WEIGHTS = {"crowd": 0.40, "interest": 0.25, "distance": 0.20, "season": 0.15}
DISTANCE_SCALE_KM = 2500


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


def weights_for(has_interest: bool, has_origin: bool) -> dict[str, float]:
    w = dict(BASE_WEIGHTS)
    if not has_interest:
        w["interest"] = 0.0
    if not has_origin:
        w["distance"] = 0.0
    total = sum(w.values())
    return {k: round(v / total, 4) for k, v in w.items()}


def interest_match(d: Destination, interest: str) -> float:
    if interest in (d.categories or []):
        return 1.0
    for a in d.attractions:
        if interest == a.category or interest in (a.tags or []):
            return 0.5
    return 0.0


def clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def recommend(destinations: list[Destination], day: dt.date, origin: dict | None, interest: str | None,
              max_km: int | None, limit: int) -> dict:
    runtime.prefetch_day([runtime.spec(a) for d in destinations for a in d.attractions], day)
    w = weights_for(bool(interest), origin is not None)
    day_label = day.strftime("%a %d %b")
    items = []
    for d in destinations:
        km = haversine_km(origin["lat"], origin["lon"], d.lat, d.lon) if origin else None
        if max_km and km is not None and km > max_km:
            continue
        hourly = prediction.aggregate_day(d, day)
        if not hourly:
            continue
        c = prediction.card(hourly)
        f: dict[str, float] = {"crowd": clamp(1 - c["crowd"]["util"] / 0.9)}
        reasons, cautions = [], []
        lvl = c["crowd"]["level"]
        people = f"{c['crowd']['visitors']:,}"
        if lvl in ("Low", "Moderate"):
            reasons.append(f"Predicted {lvl} crowds on {day_label}: about {people} people at the busiest hour "
                           f"({c['crowd']['peak_label']}), and quieter at {c['suggested_time']['label']}")
        else:
            cautions.append(f"Predicted {lvl} crowds on {day_label} around {c['crowd']['peak_label']}; "
                            f"{c['suggested_time']['label']} is the quietest time")
        if interest:
            f["interest"] = interest_match(d, interest)
            if f["interest"] == 1.0:
                reasons.append(f"A {interest} destination")
            elif f["interest"] == 0.5:
                reasons.append(f"Has {interest} attractions")
            else:
                cautions.append(f"No {interest} attractions in our data")
        if origin:
            f["distance"] = clamp(1 - km / DISTANCE_SCALE_KM)
            reasons.append(f"About {round(km):,} km from you (straight line)")
        in_season = not d.best_months or day.month in d.best_months
        f["season"] = 1.0 if in_season else 0.3
        (reasons if in_season else cautions).append(
            f"{day.strftime('%B')} is a good time to visit" if in_season else f"{day.strftime('%B')} is outside the usual best season")
        breakdown = {k: round(v, 3) for k, v in f.items() if w[k] > 0}
        score = sum(w[k] * f[k] for k in breakdown)
        items.append({"slug": d.slug, "name": d.name, "state": d.state.name, "state_code": d.state.code, "lat": d.lat, "lon": d.lon,
                      "categories": d.categories, "description": d.description, "daily_cost": d.daily_cost,
                      "score": round(score, 3), "breakdown": breakdown, "reasons": reasons[:4], "cautions": cautions[:2],
                      "distance_km": round(km) if km is not None else None, "distance_note": "straight-line distance",
                      "in_season": in_season, **c})
    items.sort(key=lambda x: (-x["score"], x["name"]))
    return {"date": day.isoformat(), "weights": w, "items": items[:limit], "total_considered": len(items),
            "method": "Each destination is scored from four factors: predicted crowd on your date, match with your interest, "
                      "distance from your start and whether it is the right season. Popularity is not used.",
            "provenance": prediction.provenance()}
