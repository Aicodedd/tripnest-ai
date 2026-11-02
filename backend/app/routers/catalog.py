"""Destination data, crowd forecasts, comparison, map data and photos (supports EPIC-001, EPIC-002)."""
from __future__ import annotations

import datetime as dt
import re
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..data.catalog import DATA_SOURCES
from ..db import get_db
from ..models import Attraction, Destination, State
from ..services import crowd, crowd_sim, photos, runtime
from ..services.explore import image_of

router = APIRouter(prefix="/api", tags=["discovery & crowd"])
SOURCE_NOTE = {k: (name, kind, desc) for k, name, kind, desc in DATA_SOURCES}


def _source(key: str) -> dict:
    name, kind, desc = SOURCE_NOTE[key]
    return {"key": key, "name": name, "kind": kind, "note": desc}


def dest_card(d: Destination) -> dict:
    return {"slug": d.slug, "name": d.name, "state": {"code": d.state.code, "name": d.state.name},
            "lat": d.lat, "lon": d.lon, "categories": d.categories, "budget": d.budget, "daily_cost": d.daily_cost,
            "min_days": d.min_days, "best_months": d.best_months, "featured": d.featured,
            "description": d.description, "attraction_count": len(d.attractions),
            "popularity": d.popularity, "image": image_of(d)}


def attraction_out(a: Attraction) -> dict:
    return {"slug": a.slug, "name": a.name, "category": a.category, "lat": a.lat, "lon": a.lon,
            "capacity": a.capacity, "open_hour": a.open_hour, "close_hour": a.close_hour, "fee": a.fee,
            "sensitive": a.sensitive, "family_friendly": a.family_friendly, "elder_friendly": a.elder_friendly,
            "covered": a.covered, "visit_min": a.visit_min, "tags": a.tags, "description": a.description,
            "thresholds": crowd.thresholds(a.sensitive)}


def get_dest(db: Session, slug: str) -> Destination:
    d = db.scalar(select(Destination).where(Destination.slug == slug)
                  .options(selectinload(Destination.attractions), selectinload(Destination.state)))
    if not d:
        raise HTTPException(404, "Destination not found")
    return d


def get_attr(db: Session, slug: str) -> Attraction:
    a = db.scalar(select(Attraction).where(Attraction.slug == slug))
    if not a:
        raise HTTPException(404, "Attraction not found")
    return a


def parse_at(at: str | None) -> dt.datetime:
    if not at:
        return runtime.now_local()
    try:
        return dt.datetime.fromisoformat(at[:16])
    except ValueError:
        raise HTTPException(422, "at must look like YYYY-MM-DDTHH:MM")


def parse_day(date: str | None) -> dt.date:
    if not date:
        return runtime.now_local().date()
    try:
        return dt.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(422, "date must look like YYYY-MM-DD")


# ------------------------------------------------------------------ catalogue
@router.get("/states")
def states(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Destination.state_id, func.count()).group_by(Destination.state_id)).all())
    rows = db.scalars(select(State).order_by(State.name)).all()
    return {"items": [{"code": s.code, "name": s.name, "kind": s.kind, "region": s.region,
                       "destinations": counts.get(s.id, 0)} for s in rows]}


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    c = Counter()
    for cats in db.scalars(select(Destination.categories)).all():
        c.update(cats or [])
    return {"items": [{"name": k, "count": v} for k, v in c.most_common()]}


@router.get("/destinations")
def destinations(q: str | None = Query(None, max_length=60), state: str | None = Query(None, max_length=4),
                 category: str | None = Query(None, max_length=30), budget: str | None = Query(None, pattern="^(low|mid|high)$"),
                 month: int | None = Query(None, ge=1, le=12), featured: bool | None = None,
                 sort: str = Query("popular", pattern="^(popular|name|cost)$"),
                 page: int = Query(1, ge=1, le=100), limit: int = Query(24, ge=1, le=60), db: Session = Depends(get_db)):
    stmt = select(Destination).join(State).options(selectinload(Destination.attractions), selectinload(Destination.state))
    if q:
        like = f"%{q.lower()}%"
        sub = select(Attraction.destination_id).where(func.lower(Attraction.name).like(like))
        stmt = stmt.where(or_(func.lower(Destination.name).like(like), func.lower(Destination.description).like(like),
                              func.lower(State.name).like(like), Destination.id.in_(sub)))
    if state:
        stmt = stmt.where(State.code == state.upper())
    if budget:
        stmt = stmt.where(Destination.budget == budget)
    if featured is not None:
        stmt = stmt.where(Destination.featured == featured)
    order = {"popular": Destination.popularity.desc(), "name": Destination.name, "cost": Destination.daily_cost}[sort]
    rows = db.scalars(stmt.order_by(order, Destination.name)).all()
    # JSON-list filters are applied in Python so they behave the same on SQLite and PostgreSQL
    if category:
        rows = [d for d in rows if category in (d.categories or []) or any(a.category == category for a in d.attractions)]
    if month:
        rows = [d for d in rows if month in (d.best_months or [])]
    if q:  # SQL LIKE pre-filters; keep only matches at the start of a word ("taj" must not match "Netaji")
        word = re.compile(r"\b" + re.escape(q.lower()))
        rows = [d for d in rows if any(word.search(t.lower()) for t in
                                       [d.name, d.description, d.state.name, *(a.name for a in d.attractions)])]
    total = len(rows)
    page_rows = rows[(page - 1) * limit: page * limit]
    return {"items": [dest_card(d) for d in page_rows], "total": total, "page": page, "limit": limit}


@router.get("/destinations/{slug}")
def destination(slug: str, db: Session = Depends(get_db)):
    d = get_dest(db, slug)
    return {**dest_card(d), "how_to_reach": d.how_to_reach, "facilities": d.facilities, "climate": d.climate,
            "attractions": [attraction_out(a) for a in d.attractions],
            "updated_at": d.updated_at.isoformat(), "provenance": {"catalogue": _source("catalogue")}}


# ------------------------------------------------------------------ crowd
def _live(db: Session, a: Attraction, at: dt.datetime) -> dict:
    s = runtime.spec(a)
    if not runtime.is_open(s, at):
        return {"slug": a.slug, "name": a.name, "category": a.category, "lat": a.lat, "lon": a.lon,
                "open": False, "level": "Closed", "util": 0.0, "visitors": 0, "reports": 0,
                "hours": [a.open_hour, a.close_hour], "sensitive": a.sensitive}
    model_u = runtime.util_at(s, at) or 0.0
    b = {"util": model_u, "reports": 0}  # model prediction only; no live source is used
    nxt = runtime.util_at(s, at + dt.timedelta(hours=1))
    trend = None if nxt is None else ("rising" if nxt - model_u > 0.06 else "falling" if model_u - nxt > 0.06 else "steady")
    return {"slug": a.slug, "name": a.name, "category": a.category, "lat": a.lat, "lon": a.lon, "open": True,
            "util": round(b["util"], 3), "visitors": int(round(b["util"] * a.capacity)), "capacity": a.capacity,
            "level": crowd.level_of(b["util"], a.sensitive), "reports": b["reports"], "trend": trend,
            "hours": [a.open_hour, a.close_hour], "sensitive": a.sensitive}


@router.get("/destinations/{slug}/crowd")
def destination_crowd(slug: str, at: str | None = None, db: Session = Depends(get_db)):
    d = get_dest(db, slug)
    t = parse_at(at)
    rows = [_live(db, a, t) for a in d.attractions]
    open_rows = [r for r in rows if r["open"]]
    if open_rows:
        u = sum(r["util"] * r["capacity"] for r in open_rows) / sum(r["capacity"] for r in open_rows)
        overall = {"util": round(u, 3), "level": crowd.level_of(u, False), "open": len(open_rows)}
    else:
        overall = {"util": 0.0, "level": "Closed", "open": 0}
    return {"destination": d.slug, "at": t.isoformat(timespec="minutes"), "overall": overall, "attractions": rows,
            "provenance": runtime.provenance(sum(r["reports"] for r in rows))}


@router.get("/attractions/{slug}/forecast")
def attraction_forecast(slug: str, date: str | None = None, db: Session = Depends(get_db)):
    a = get_attr(db, slug)
    day = parse_day(date)
    s = runtime.spec(a)
    hourly = runtime.day_forecast(s, day)
    m = runtime.model()
    return {"attraction": {**attraction_out(a), "destination": {"slug": a.destination.slug, "name": a.destination.name}},
            "date": day.isoformat(), "hourly": hourly, "peak": crowd.peak(hourly),
            "best_times": crowd.best_times(m, s, day, days=7, n=5),
            "calendar": crowd_sim.holiday(day), "in_season": crowd_sim.in_season(s, day.month),
            "capacity": {"value": a.capacity, "assumed": True,
                         "note": "Carrying capacity is an assumption for the demo, not an official figure."},
            "uncertainty": "Low/high give an 80% band from the model's test-period error.",
            "provenance": runtime.provenance()}


@router.get("/attractions/{slug}/history")
def attraction_history(slug: str, db: Session = Depends(get_db)):
    a = get_attr(db, slug)
    s = runtime.spec(a)
    end = runtime.now_local().date()
    df = crowd_sim.counts([s], crowd_sim.date_range(end, 364))
    df["util"] = df["count"] / a.capacity
    df["dow"] = [x.weekday() for x in df["date"]]
    df["month"] = [x.month for x in df["date"]]
    recent = df[df["date"] >= end - dt.timedelta(days=56)]
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    by_wd = []
    for wd in range(7):
        g = recent[recent["dow"] == wd].groupby("hour")["util"].mean()
        by_wd.append({"weekday": names[wd], "hourly": [{"hour": int(h), "util": round(float(u), 3)} for h, u in g.items()],
                      "peak_util": round(float(g.max()), 3) if len(g) else 0.0})
    daily_peak = df.groupby(["month", "date"])["util"].max().groupby("month").mean()
    by_month = [{"month": int(m), "avg_peak_util": round(float(u), 3)} for m, u in daily_peak.items()]
    return {"attraction": a.slug, "by_weekday": by_wd, "by_month": by_month,
            "period": {"from": (end - dt.timedelta(days=364)).isoformat(), "to": end.isoformat()},
            "provenance": {"type": "historical-demonstration", "source": _source("crowd-demo"),
                           "note": "Patterns from simulated demonstration history, not recorded visitor counts."}}


@router.get("/crowd/compare")
def compare(slugs: str = Query(..., max_length=400), date: str | None = None, db: Session = Depends(get_db)):
    keys = [s.strip() for s in slugs.split(",") if s.strip()]
    if not 1 <= len(keys) <= 5:
        raise HTTPException(422, "Compare between 1 and 5 destinations")
    day = parse_day(date)
    items = []
    for k in keys:
        d = get_dest(db, k)
        per_h: dict[int, list] = {}
        for a in d.attractions:
            for h in runtime.day_forecast(runtime.spec(a), day):
                per_h.setdefault(h["hour"], []).append((h["visitors"], a.capacity))
        hourly = [{"hour": h, "util": round(sum(v for v, _ in xs) / sum(c for _, c in xs), 3)}
                  for h, xs in sorted(per_h.items())]
        for h in hourly:
            h["level"] = crowd.level_of(h["util"], False)
        pk = max(hourly, key=lambda h: h["util"]) if hourly else None
        quiet = min((h for h in hourly if 8 <= h["hour"] <= 18), key=lambda h: h["util"], default=None)
        items.append({"slug": d.slug, "name": d.name, "hourly": hourly, "peak": pk, "quietest": quiet})
    return {"date": day.isoformat(), "items": items, "provenance": runtime.provenance()}


@router.get("/model")
def model_card():
    return runtime.model().info


# ------------------------------------------------------------------ reviews
def review_out(r: Review) -> dict:
    return {"id": r.id, "rating": r.rating, "text": r.text, "sentiment": r.sentiment, "score": r.score,
            "aspects": r.aspects, "source": r.source,
            "author": r.user.name if r.user else ("Demo review" if r.source == "demo" else "Traveller"),
            "attraction": r.attraction.name if r.attraction else None, "created_at": r.created_at.isoformat()}


@router.get("/crowd/highlights")
def highlights(date: str | None = None, limit: int = Query(12, ge=1, le=30), db: Session = Depends(get_db)):
    """For featured destinations: the busiest hour of their most popular attraction and its quietest hour."""
    day = parse_day(date)
    dests = db.scalars(select(Destination).where(Destination.featured.is_(True))
                       .options(selectinload(Destination.attractions), selectinload(Destination.state))
                       .order_by(Destination.popularity.desc(), Destination.name)).all()
    items = []
    runtime.prefetch_day([runtime.spec(a) for d in dests[:limit] for a in d.attractions], day)
    for d in dests[:limit]:
        if not d.attractions:
            continue
        a = max(d.attractions, key=lambda x: x.popularity)
        hourly = runtime.day_forecast(runtime.spec(a), day)
        if not hourly:
            continue
        pk = crowd.peak(hourly)
        quiet = min((h for h in hourly if 7 <= h["hour"] <= 19), key=lambda h: h["util"], default=hourly[0])
        items.append({"attraction": a.name, "attraction_slug": a.slug, "destination": {"slug": d.slug, "name": d.name},
                      "state": d.state.name, "peak": pk, "quietest": quiet})
    return {"date": day.isoformat(), "items": items, "provenance": runtime.provenance()}


# ------------------------------------------------------------------ crowd heat map
HEAT_FLOOR = {"Moderate": 0.35, "High": 0.65, "At Capacity": 0.9}


def heat_of(util: float, level: str) -> float:
    """Map intensity 0..1. Low and closed places get 0 so the map stays uncoloured where it is quiet."""
    if level not in HEAT_FLOOR:
        return 0.0
    return round(min(1.0, max(HEAT_FLOOR[level], util)), 3)


@router.get("/crowd/map")
def crowd_map(at: str | None = None, destination: str | None = Query(None, max_length=80), db: Session = Depends(get_db)):
    t = parse_at(at)
    stmt = select(Attraction).options(selectinload(Attraction.destination))
    if destination:
        stmt = stmt.join(Destination).where(Destination.slug == destination)
    attrs = db.scalars(stmt).all()
    specs = [runtime.spec(a) for a in attrs]
    for day in {t.date(), (t + dt.timedelta(hours=1)).date()}:
        runtime.prefetch_day(specs, day)
    points = []
    for a in attrs:
        live = _live(db, a, t)
        points.append({"slug": a.slug, "name": a.name, "destination": a.destination.slug,
                       "destination_name": a.destination.name, "lat": a.lat, "lon": a.lon, "level": live["level"],
                       "util": live["util"], "visitors": live["visitors"], "heat": heat_of(live["util"], live["level"])})
    return {"at": t.isoformat(timespec="minutes"), "points": points, "provenance": runtime.provenance()}


# ------------------------------------------------------------------ photos
@router.get("/attractions/{slug}/photo")
def attraction_photo(slug: str, db: Session = Depends(get_db)):
    a = get_attr(db, slug)
    return photos.lookup(f"{a.name} {a.destination.name}")


@router.get("/destinations/{slug}/photo")
def destination_photo(slug: str, db: Session = Depends(get_db)):
    d = get_dest(db, slug)
    if d.image_url:  # the stored photo is used for every card, so one destination always shows the same picture
        return {"available": True, "url": d.image_url, "title": d.image_title, "credit": d.image_credit, "licence": d.image_licence,
                "source_page": d.image_source_page, "article": d.image_source_page, "source": "Wikipedia / Wikimedia Commons"}
    return photos.lookup(f"{d.name} {d.state.name} tourism")

