"""LEGACY (unmounted): crowd reports, weather and reviews. Outside the two-feature scope; kept for restoration.
To restore, include `legacy_extras.router` in app/main.py."""
from __future__ import annotations

import datetime as dt
import re
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..data.catalog import DATA_SOURCES
from ..db import get_db
from ..deps import current_user
from ..models import Attraction, CrowdReport, DataSource, Destination, Review, State, User
from ..schemas import CrowdReportIn, ReviewIn
from ..services import crowd, crowd_sim, photos, runtime, sentiment, weather
from .catalog import _source, get_attr, get_dest, parse_at

router = APIRouter(prefix="/api", tags=["legacy"])
SOURCE_NOTE = {k: (name, kind, desc) for k, name, kind, desc in DATA_SOURCES}
REPORT_WINDOW = dt.timedelta(minutes=90)


@router.post("/attractions/{slug}/reports", status_code=201)
def report_crowd(slug: str, body: CrowdReportIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    a = get_attr(db, slug)
    now = runtime.now_local()
    at = body.at.replace(tzinfo=None) if body.at else now
    if not (now - dt.timedelta(days=30) <= at <= now + dt.timedelta(days=60)):
        raise HTTPException(422, "Report time must be close to the present")
    db.add(CrowdReport(attraction_id=a.id, user_id=user.id, level=body.level, note=body.note, created_at=at))
    db.commit()
    return {"ok": True, "live": _live(db, a, at)}


@router.get("/destinations/{slug}/weather")
def destination_weather(slug: str, db: Session = Depends(get_db)):
    d = get_dest(db, slug)
    src = db.scalar(select(DataSource).where(DataSource.key == "open-meteo"))
    if src is not None and not src.enabled:
        return {"available": False, "reason": "Live weather has been disabled by an administrator.", "source": "Open-Meteo"}
    return weather.forecast(d.lat, d.lon)


@router.get("/destinations/{slug}/reviews")
def reviews(slug: str, db: Session = Depends(get_db)):
    d = get_dest(db, slug)
    rows = db.scalars(select(Review).where(Review.destination_id == d.id, Review.status == "visible")
                      .order_by(Review.created_at.desc(), Review.id.desc())).all()
    senti = Counter({"positive": 0, "neutral": 0, "negative": 0})
    senti.update(r.sentiment for r in rows)
    neg, pos = Counter(), Counter()
    labels = {}
    for r in rows:
        for x in r.aspects or []:
            labels[x["aspect"]] = x["label"]
            (neg if x["sentiment"] == "negative" else pos if x["sentiment"] == "positive" else Counter())[x["aspect"]] += 1
    summary = {"count": len(rows), "average": round(sum(r.rating for r in rows) / len(rows), 1) if rows else None,
               "sentiment": dict(senti),
               "complaints": [{"aspect": k, "label": labels[k], "count": v} for k, v in neg.most_common(5)],
               "praise": [{"aspect": k, "label": labels[k], "count": v} for k, v in pos.most_common(5)],
               "demo_count": sum(r.source == "demo" for r in rows)}
    return {"items": [review_out(r) for r in rows[:50]], "summary": summary,
            "method": "Lexicon + rules aspect-based sentiment (transparent baseline).",
            "provenance": {"demo": _source("demo-reviews")}}


@router.post("/destinations/{slug}/reviews", status_code=201)
def add_review(slug: str, body: ReviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = get_dest(db, slug)
    attr = None
    if body.attraction:
        attr = next((a for a in d.attractions if a.slug == body.attraction), None)
        if not attr:
            raise HTTPException(422, "That attraction is not part of this destination")
    res = sentiment.analyze(body.text, body.rating)
    r = Review(destination_id=d.id, attraction_id=attr.id if attr else None, user_id=user.id, rating=body.rating,
               text=body.text.strip(), sentiment=res["label"], score=res["score"], aspects=res["aspects"], source="user")
    db.add(r)
    db.commit()
    db.refresh(r)
    return review_out(r)


REPORT_WINDOW = dt.timedelta(minutes=90)


def _live(db, a, at):
    """Model estimate blended with recent traveller reports (legacy)."""
    s = runtime.spec(a)
    base = runtime.util_at(s, at) or 0.0
    reps = db.scalars(select(CrowdReport.level).where(CrowdReport.attraction_id == a.id, CrowdReport.created_at >= at - REPORT_WINDOW,
                                                      CrowdReport.created_at <= at)).all()
    b = crowd.blend_reports(base, list(reps))
    return {"slug": a.slug, "util": round(b["util"], 3), "level": crowd.level_of(b["util"], a.sensitive), "reports": b["reports"]}
