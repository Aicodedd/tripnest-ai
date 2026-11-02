"""The two core features: location handling, crowd prediction for a destination, and recommendations."""
from __future__ import annotations

import datetime as dt

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..data import cities
from ..db import get_db
from ..models import Destination
from ..services import explore as explore_service, prediction, recommender

router = APIRouter(prefix="/api", tags=["crowd prediction & recommendation"])


def travel_date(value: str) -> dt.date:
    """A travel date from today minus a year to 18 months ahead."""
    try:
        d = dt.date.fromisoformat(value)
    except ValueError:
        raise HTTPException(422, "date must look like YYYY-MM-DD")
    today = dt.date.today()
    if not (today - dt.timedelta(days=365) <= d <= today + dt.timedelta(days=548)):
        raise HTTPException(422, "Choose a date within the next 18 months")
    return d


# ------------------------------------------------------------------ locations
@router.get("/locations/search", summary="Search Indian cities by name")
def search_locations(q: str = Query(..., min_length=2, max_length=60)):
    return {"items": cities.search(q)}


@router.get("/locations/resolve", summary="Resolve typed text to a city (manual entry)")
def resolve_location(q: str = Query(..., min_length=1, max_length=80)):
    hit = cities.resolve(q)
    if not hit:
        raise HTTPException(404, f"We couldn't find “{q.strip()[:40]}”. Pick a suggestion, or enter a nearby major city.")
    return hit


@router.get("/locations/nearest", summary="The nearest listed city to a position (used for the greeting)")
def nearest_location(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180)):
    return cities.nearest(lat, lon)


@router.get("/locations/all", summary="All cities available as starting points")
def all_locations():
    return {"items": [cities.as_dict(c) for c in cities.CITIES]}


# ------------------------------------------------------------------ core feature 1: crowd prediction
@router.get("/destinations/{slug}/prediction", summary="Predicted crowd for a destination, date and time range")
def destination_prediction(slug: str, date: str = Query(...), from_hour: int = Query(8, alias="from", ge=0, le=23),
                           to_hour: int = Query(18, alias="to", ge=0, le=23), db: Session = Depends(get_db)):
    day = travel_date(date)
    if from_hour > to_hour:
        raise HTTPException(422, "The start of the time range must not be after its end")
    d = db.scalar(select(Destination).where(Destination.slug == slug)
                  .options(selectinload(Destination.attractions), selectinload(Destination.state)))
    if not d:
        raise HTTPException(404, "Destination not found")
    out = prediction.predict(d, day, from_hour, to_hour)
    out["destination"] = {"image": explore_service.image_of(d), "slug": d.slug, "name": d.name, "state": d.state.name, "state_code": d.state.code, "lat": d.lat,
                          "lon": d.lon, "categories": d.categories, "description": d.description,
                          "how_to_reach": d.how_to_reach, "best_months": d.best_months, "daily_cost": d.daily_cost,
                          "min_days": d.min_days, "facilities": d.facilities, "climate": d.climate,
                          "updated_at": d.updated_at.isoformat(), "data_source": "TripNest catalogue (public knowledge; indicative)"}
    return out


# ------------------------------------------------------------------ core feature 2: recommendation
@router.get("/recommendations", summary="Recommended destinations for a start, date and optional interest")
def recommendations(date: str = Query(...), lat: float | None = Query(None, ge=-90, le=90), lon: float | None = Query(None, ge=-180, le=180),
                    interest: str | None = Query(None, max_length=30, pattern=r"^[A-Za-z][A-Za-z \-]*$"),
                    max_km: int | None = Query(None, ge=10, le=5000), limit: int = Query(6, ge=1, le=60),
                    db: Session = Depends(get_db)):
    day = travel_date(date)
    if (lat is None) != (lon is None):
        raise HTTPException(422, "Give both lat and lon, or neither")
    origin = {"lat": lat, "lon": lon} if lat is not None else None
    dests = db.scalars(select(Destination).options(selectinload(Destination.attractions), selectinload(Destination.state))).all()
    return recommender.recommend(dests, day, origin, interest.lower().strip() if interest else None, max_km, limit)


# ------------------------------------------------------------------ both features together: location-first discovery
@router.get("/explore", summary="Popular places and hidden gems around a location, with predicted crowds")
def explore(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180), date: str = Query(...),
            interest: str | None = Query(None, max_length=30, pattern=r"^[A-Za-z][A-Za-z \-]*$"),
            slot: Literal["all", "early", "morning", "afternoon", "evening"] = "all", db: Session = Depends(get_db)):
    day = travel_date(date)
    origin = cities.nearest(lat, lon)
    origin["lat"], origin["lon"] = lat, lon
    if not origin["covered"]:
        return {"date": day.isoformat(), "slot": slot, "origin": origin, "popular": [], "hidden_gems": [], "map": [],
                "message": origin["message"], "provenance": prediction.provenance()}
    dests = db.scalars(select(Destination).options(selectinload(Destination.attractions), selectinload(Destination.state))).all()
    return explore_service.discover(dests, day, origin, interest.lower().strip() if interest else None, slot)
