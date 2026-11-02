"""Recommendations (EPIC-005) and itineraries (EPIC-006)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..deps import current_user
from ..models import Attraction, Destination, Itinerary, User
from ..schemas import ItineraryEditIn, ItinerarySaveIn, PlanIn, RecommendIn, RegenerateIn
from ..services import planner, recommender, weather

router = APIRouter(prefix="/api", tags=["recommendations & itineraries"])


@router.post("/recommendations")
def recommendations(body: RecommendIn, db: Session = Depends(get_db)):
    dests = db.scalars(select(Destination).options(selectinload(Destination.attractions),
                                                   selectinload(Destination.state))).all()
    return recommender.recommend(dests, body)


def _load_dests(db: Session, slugs: list[str]) -> list[Destination]:
    out = []
    for s in slugs:
        d = db.scalar(select(Destination).where(Destination.slug == s).options(selectinload(Destination.attractions)))
        if not d:
            raise HTTPException(404, f"Destination '{s}' not found")
        out.append(d)
    return out


def _weather(dests: list[Destination]) -> dict:
    return {d.slug: weather.rain_by_hour(d.lat, d.lon) for d in dests}


def _generate(db: Session, p: PlanIn) -> dict:
    dests = _load_dests(db, p.destinations)
    return planner.generate(dests, p.start_date, p.days, p.interests, p.group_type, p.pace, _weather(dests))


@router.post("/itineraries/generate")
def generate(body: PlanIn, db: Session = Depends(get_db)):
    return {"params": body.model_dump(mode="json"), "plan": _generate(db, body)}


def it_out(it: Itinerary) -> dict:
    return {"id": it.id, "title": it.title, "start_date": it.start_date.isoformat(), "days": it.days,
            "params": it.params, "plan": it.plan, "notes": it.notes, "created_at": it.created_at.isoformat(),
            "updated_at": it.updated_at.isoformat()}


def _own(db: Session, iid: int, user: User) -> Itinerary:
    it = db.get(Itinerary, iid)
    if not it or it.user_id != user.id:
        raise HTTPException(404, "Itinerary not found")
    return it


@router.post("/itineraries", status_code=201)
def save(body: ItinerarySaveIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    params = PlanIn(**body.model_dump(exclude={"title"}))
    it = Itinerary(user_id=user.id, title=body.title.strip(), start_date=body.start_date, days=body.days,
                   params=params.model_dump(mode="json"), plan=_generate(db, params))
    db.add(it)
    db.commit()
    return it_out(it)


@router.get("/itineraries")
def mine(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Itinerary).where(Itinerary.user_id == user.id).order_by(Itinerary.updated_at.desc())).all()
    return {"items": [{"id": i.id, "title": i.title, "start_date": i.start_date.isoformat(), "days": i.days,
                       "destinations": [d["destination"]["name"] for d in i.plan.get("days", [])],
                       "updated_at": i.updated_at.isoformat()} for i in rows]}


@router.get("/itineraries/{iid}")
def one(iid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return it_out(_own(db, iid, user))


@router.put("/itineraries/{iid}")
def edit(iid: int, body: ItineraryEditIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    it = _own(db, iid, user)
    if body.title is not None:
        it.title = body.title.strip()
    if body.notes is not None:
        it.notes = body.notes
    if body.days is not None:
        old_days = it.plan.get("days", [])
        if len(body.days) > len(old_days):
            raise HTTPException(422, "An edit cannot add days; regenerate with more days instead")
        slugs = [s for d in body.days for s in d.stops]
        if len(slugs) != len(set(slugs)):
            raise HTTPException(422, "Each attraction can appear only once in a trip")
        found = {a.slug: a for a in db.scalars(select(Attraction).where(Attraction.slug.in_(slugs))).all()}
        missing = [s for s in slugs if s not in found]
        if missing:
            raise HTTPException(422, f"Unknown attraction(s): {', '.join(missing)}")
        edits = [[found[s] for s in d.stops] for d in body.days]
        edits += [[found_or_db(db, s["slug"]) for s in d["stops"]] for d in old_days[len(body.days):]]
        it.plan = planner.retime(it.plan, edits, it.params.get("pace", "normal"))
    db.add(it)
    db.commit()
    return it_out(it)


def found_or_db(db: Session, slug: str) -> Attraction:
    a = db.scalar(select(Attraction).where(Attraction.slug == slug))
    if not a:
        raise HTTPException(422, f"Attraction '{slug}' no longer exists")
    return a


@router.post("/itineraries/{iid}/regenerate")
def regenerate(iid: int, body: RegenerateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    it = _own(db, iid, user)
    params = PlanIn(**{**it.params, **body.model_dump(exclude_none=True)})
    it.params = params.model_dump(mode="json")
    it.plan = _generate(db, params)
    db.add(it)
    db.commit()
    return it_out(it)


@router.delete("/itineraries/{iid}")
def delete(iid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    it = _own(db, iid, user)
    db.delete(it)
    db.commit()
    return {"ok": True}
