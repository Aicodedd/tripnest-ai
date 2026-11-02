"""Location-first discovery: popular places near a location, hidden gems that are calmer, and map points.

Classification uses the catalogue's popularity score (an ASSUMPTION about how well known a place is, not a visitor
statistic): >= POPULAR_MIN is "popular", <= GEM_MAX is "lesser-known" (a hidden-gem candidate), in between is "other".
A lesser-known place is only offered as an escape when its predicted crowd on the chosen date is Low or Moderate.
"""
from __future__ import annotations

import datetime as dt

from ..models import Destination
from . import prediction, recommender, runtime

POPULAR_MIN = 0.9
GEM_MAX = 0.8
RADIUS_KM = 800        # popular places
GEM_RADIUS_KM = 500    # hidden gems should be near
MAX_ALT_KM = 200       # a "calmer alternative to X" must be this close to X
GENERIC = {"viewpoint", "nature", "food", "market", "family", "culture", "heritage", "spiritual"}  # too vague to call two places alternatives
COLOR = {"Low": "green", "Moderate": "yellow", "High": "red", "At Capacity": "red", "Closed": "grey"}
COLOR_LABEL = {"green": "Low crowd", "yellow": "Moderate crowd", "red": "High crowd", "grey": "Closed"}


def group_of(popularity: float) -> str:
    return "popular" if popularity >= POPULAR_MIN else "hidden_gem" if popularity <= GEM_MAX else "other"


def image_of(d: Destination) -> dict | None:
    if not d.image_url:
        return None
    return {"url": d.image_url, "title": d.image_title, "credit": d.image_credit, "licence": d.image_licence,
            "source_page": d.image_source_page}


def _short(text: str, n: int = 130) -> str:
    text = text.strip()
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def _item(d: Destination, hourly: list[dict], km: float, slot: str) -> dict:
    pk = prediction.slot_peak(hourly, slot) or prediction.slot_peak(hourly, "all")
    crowd = ({"level": pk["level"], "util": pk["util"], "visitors": pk["visitors"], "low": pk["low"], "high": pk["high"],
              "peak_hour": pk["hour"], "peak_label": pk["label"], "slot": slot} if pk else
             {"level": "Closed", "util": 0.0, "visitors": 0, "low": 0, "high": 0, "peak_hour": None, "peak_label": None, "slot": slot})
    color = COLOR[crowd["level"]]
    bw = prediction.best_window(hourly)
    return {"slug": d.slug, "name": d.name, "state": d.state.name, "state_code": d.state.code, "lat": d.lat, "lon": d.lon,
            "categories": d.categories, "description": d.description, "popularity": d.popularity, "group": group_of(d.popularity),
            "image": image_of(d), "distance_km": round(km), "distance_note": "straight-line distance", "crowd": crowd,
            "crowd_display": {"color": color, "label": COLOR_LABEL[color], "near_capacity": crowd["level"] == "At Capacity"},
            "timeline": prediction.timeline(hourly), "best_window": bw,
            "best_label": bw["label"] if bw["available"] else "No quiet time predicted"}


def _point(it: dict) -> dict:
    return {"slug": it["slug"], "name": it["name"], "state": it["state"], "lat": it["lat"], "lon": it["lon"], "group": it["group"],
            "level": it["crowd"]["level"], "color": it["crowd_display"]["color"], "util": it["crowd"]["util"],
            "distance_km": it["distance_km"], "image_url": it["image"]["url"] if it["image"] else None,
            "blurb": _short(it["description"]), "best_label": it["best_label"], "peak_label": it["crowd"]["peak_label"]}


def discover(destinations: list[Destination], day: dt.date, origin: dict, interest: str | None, slot: str,
             limit_popular: int = 6, limit_gems: int = 6) -> dict:
    runtime.prefetch_day([runtime.spec(a) for d in destinations for a in d.attractions], day)
    label = origin["label"]
    day_label = day.strftime("%a %d %b")
    items: list[dict] = []
    for d in destinations:
        hourly = prediction.aggregate_day(d, day)
        if not hourly:
            continue
        km = recommender.haversine_km(origin["lat"], origin["lon"], d.lat, d.lon)
        it = _item(d, hourly, km, slot)
        it["_match"] = recommender.interest_match(d, interest) if interest else 0.0
        it["_season"] = not d.best_months or day.month in d.best_months
        items.append(it)

    # ---- popular places near the location
    pop_all = sorted((i for i in items if i["group"] == "popular"),
                     key=lambda i: (-i["_match"], i["distance_km"]) if interest else (i["distance_km"],))
    near = [i for i in pop_all if i["distance_km"] <= RADIUS_KM]
    pop_expanded = len(near) < 3
    popular = (sorted(pop_all, key=lambda i: i["distance_km"]) if pop_expanded else near)[:limit_popular]
    if interest and not pop_expanded:
        popular = sorted(near, key=lambda i: (-i["_match"], i["distance_km"]))[:limit_popular]
    for i in popular:
        c = i["crowd"]
        i["classification_reason"] = (f"Popular: catalogue popularity score {i['popularity']} "
                                      f"(places scoring {POPULAR_MIN} or more count as popular; a catalogue assumption, not a visitor count).")
        i["reasons"] = [f"{i['distance_km']:,} km from {label} (straight line)",
                        f"Predicted {c['level']} crowd on {day_label}"
                        + (f", busiest around {c['peak_label']}" if c["peak_label"] else "")]
        if interest and i["_match"] >= 0.5:
            i["reasons"].append(f"Matches your interest: {interest}")
        if i["best_window"]["available"]:
            i["reasons"].append(f"Best time {i['best_window']['label']}")

    # ---- hidden gems: lesser-known, calmer, ranked by the same transparent score used for recommendations
    w = recommender.weights_for(bool(interest), True)
    gem_all = [i for i in items if i["group"] == "hidden_gem"]
    gem_near = [i for i in gem_all if i["distance_km"] <= GEM_RADIUS_KM]
    gem_expanded = len(gem_near) < 3
    pool = sorted(gem_all, key=lambda i: i["distance_km"])[:12] if gem_expanded else gem_near
    for i in pool:
        f = {"crowd": recommender.clamp(1 - i["crowd"]["util"] / 0.9), "distance": recommender.clamp(1 - i["distance_km"] / recommender.DISTANCE_SCALE_KM),
             "season": 1.0 if i["_season"] else 0.3}
        if interest:
            f["interest"] = i["_match"]
        i["breakdown"] = {k: round(v, 3) for k, v in f.items() if w[k] > 0}
        i["score"] = round(sum(w[k] * f[k] for k in i["breakdown"]), 3)
    pool.sort(key=lambda i: (-i["score"], i["name"]))
    calm = [i for i in pool if i["crowd"]["level"] in ("Low", "Moderate")]
    gems = calm[:limit_gems]
    gems_busy_note = None
    if len(gems) < 3:
        gems += [i for i in pool if i not in gems][: 3 - len(gems)]
        gems_busy_note = f"Most lesser-known places near you are also expected to be busy on {day_label}; consider another date."
    pop_by_slug = {i["slug"]: i for i in pop_all}
    for g in gems:
        c = g["crowd"]
        g["classification_reason"] = (f"Lesser-known: catalogue popularity score {g['popularity']} "
                                      f"(places scoring {GEM_MAX} or less count as lesser-known; a catalogue assumption, not a visitor count).")
        alt = None
        gcat = set(next((d.categories for d in destinations if d.slug == g["slug"]), [])[:3])
        for p in pop_by_slug.values():
            km_pg = recommender.haversine_km(g["lat"], g["lon"], p["lat"], p["lon"])
            if km_pg <= MAX_ALT_KM and (gcat & set(p["categories"])) - GENERIC and p["crowd"]["level"] in ("High", "At Capacity") \
                    and p["crowd"]["util"] > c["util"] + 0.1:
                if alt is None or p["crowd"]["util"] > alt["crowd"]["util"]:
                    alt = p
        g["alternative_to"] = {"slug": alt["slug"], "name": alt["name"], "level": alt["crowd"]["level"]} if alt else None
        reasons = [f"Quieter option: predicted {c['level']} crowd on {day_label}"
                   + (f", about {c['visitors']:,} people at the busiest time" if c["visitors"] else "")]
        if alt:
            reasons.append(f"A calmer alternative to {alt['name']}, which is predicted {alt['crowd']['level']} on {day_label}")
        else:
            reasons.append("Looking for a quieter experience? This destination has a lower predicted crowd level for your date.")
        if interest and g["_match"] >= 0.5:
            reasons.append(f"Matches your interest: {interest}")
        reasons.append(f"{g['distance_km']:,} km from {label} (straight line)")
        if c["level"] not in ("Low", "Moderate"):
            reasons.append("Caution: this place is also predicted to be busy on your date")
        g["reasons"] = reasons

    # ---- map points: everything within reach, so filters can work in the browser
    reach = max([RADIUS_KM] + [i["distance_km"] for i in popular + gems])
    shown_gems = {g["slug"] for g in gems}
    points = []
    for i in sorted(items, key=lambda i: i["distance_km"]):
        if i["distance_km"] > reach:
            continue
        pt = _point(i)
        if i["group"] == "hidden_gem" and i["slug"] not in shown_gems:
            pt["group"] = "other"          # lesser-known but not recommended (busy, or not near enough): never called a hidden gem
            pt["lesser_known"] = True
        points.append(pt)
    for i in items:
        for k in ("_match", "_season"):
            i.pop(k, None)
    note = lambda n: f"Fewer than three popular places lie within {RADIUS_KM} km, so these are the nearest in our catalogue." if n else None  # noqa: E731
    return {"date": day.isoformat(), "slot": slot, "origin": origin, "popular": popular, "popular_expanded": pop_expanded,
            "popular_note": note(pop_expanded), "hidden_gems": gems, "gems_expanded": gem_expanded,
            "gems_note": (gems_busy_note or (f"Fewer than three lesser-known places lie within {GEM_RADIUS_KM} km, so these are the nearest in our catalogue." if gem_expanded else None)),
            "map": points, "radius_km": RADIUS_KM, "gem_radius_km": GEM_RADIUS_KM,
            "classification": {"popular_min": POPULAR_MIN, "gem_max": GEM_MAX,
                               "note": "Popularity is a score in our catalogue (an assumption about how well known a place is), not a visitor count. "
                                       "A hidden gem is a lesser-known place that is also predicted to be calm on your date."},
            "method": "Popular places are the nearest well-known destinations. Hidden gems are lesser-known destinations ranked by predicted "
                      "crowd on your date, distance, season and interest (same transparent score as recommendations).",
            "provenance": prediction.provenance()}
