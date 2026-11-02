"""Administration (EPIC-009). Every route requires role=admin."""
from __future__ import annotations

import datetime as dt
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..db import get_db
from ..deps import admin_user
from ..models import (Attraction, Comment, ContentReport, CrowdReport, DataSource, Destination, Itinerary, Listing,
                      Post, Review, State, User)
from ..schemas import (AttractionIn, AttractionPatch, DataSourcePatch, DestinationIn, DestinationPatch, ListingIn,
                       ListingPatch, ReportPatch, StatusPatch, UserPatch)
from ..services import crowd, runtime
from ..services.seed import slugify
from .catalog import attraction_out, dest_card, get_dest, parse_at

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(admin_user)])
STARTED = time.time()


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    c = lambda m: db.scalar(select(func.count()).select_from(m))  # noqa: E731
    return {"users": c(User), "destinations": c(Destination), "attractions": c(Attraction), "reviews": c(Review),
            "posts": c(Post), "itineraries": c(Itinerary), "crowd_reports": c(CrowdReport),
            "open_reports": db.scalar(select(func.count()).select_from(ContentReport).where(ContentReport.status == "open"))}


@router.get("/alerts")
def alerts(at: str | None = None, hours: int = Query(6, ge=1, le=12), db: Session = Depends(get_db)):
    """Attractions predicted to reach High / At Capacity in the next `hours`."""
    t = parse_at(at)
    out = []
    attrs = db.scalars(select(Attraction).options(selectinload(Attraction.destination))).all()
    runtime.prefetch_day([runtime.spec(a) for a in attrs], t.date())
    for a in attrs:
        s = runtime.spec(a)
        fc = {h["hour"]: h for h in runtime.day_forecast(s, t.date())}
        window = [fc[h] for h in range(t.hour, min(24, t.hour + hours)) if h in fc]
        if not window:
            continue
        pk = max(window, key=lambda h: h["util"])
        if pk["level"] in ("High", "At Capacity"):
            out.append({"slug": a.slug, "name": a.name, "destination": a.destination.name, "hour": pk["hour"],
                        "lead_hours": pk["hour"] - t.hour, "util": pk["util"], "level": pk["level"],
                        "p_exceed": pk["p_exceed"], "sensitive": a.sensitive,
                        "action": ("Enforce visitor cap and show conservation notice" if a.sensitive and pk["level"] == "At Capacity"
                                   else "Redirect visitors to nearby alternatives; add staff at entry and parking"
                                   if pk["level"] == "At Capacity" else "Monitor; nudge arrivals to quieter hours")})
    out.sort(key=lambda x: (-x["p_exceed"], -x["util"]))
    return {"at": t.isoformat(timespec="minutes"), "items": out[:60], "provenance": runtime.provenance()}


# ------------------------------------------------------------------ destinations & attractions
@router.post("/destinations", status_code=201)
def create_destination(body: DestinationIn, db: Session = Depends(get_db)):
    st = db.scalar(select(State).where(State.code == body.state_code.upper()))
    if not st:
        raise HTTPException(422, "Unknown state code")
    if db.scalar(select(Destination.id).where(Destination.slug == body.slug)):
        raise HTTPException(409, "Slug already in use")
    d = Destination(**body.model_dump(exclude={"state_code"}), state_id=st.id, source="admin")
    db.add(d)
    db.commit()
    return dest_card(get_dest(db, d.slug))


@router.put("/destinations/{slug}")
def update_destination(slug: str, body: DestinationPatch, db: Session = Depends(get_db)):
    d = get_dest(db, slug)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    db.commit()
    runtime._cache.clear()
    return dest_card(d)


@router.delete("/destinations/{slug}")
def delete_destination(slug: str, db: Session = Depends(get_db)):
    d = get_dest(db, slug)
    db.delete(d)
    db.commit()
    return {"ok": True}


def _attr(db: Session, slug: str) -> Attraction:
    a = db.scalar(select(Attraction).where(Attraction.slug == slug))
    if not a:
        raise HTTPException(404, "Attraction not found")
    return a


@router.post("/attractions", status_code=201)
def create_attraction(body: AttractionIn, db: Session = Depends(get_db)):
    d = get_dest(db, body.destination)
    if body.close_hour <= body.open_hour:
        raise HTTPException(422, "close_hour must be after open_hour")
    slug = f"{d.slug}-{slugify(body.name)}"
    if db.scalar(select(Attraction.id).where(Attraction.slug == slug)):
        raise HTTPException(409, "An attraction with this name already exists here")
    a = Attraction(**body.model_dump(exclude={"destination"}), destination_id=d.id, slug=slug, source="admin")
    db.add(a)
    db.commit()
    return attraction_out(a)


@router.put("/attractions/{slug}")
def update_attraction(slug: str, body: AttractionPatch, db: Session = Depends(get_db)):
    a = _attr(db, slug)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    if a.close_hour <= a.open_hour:
        db.rollback()
        raise HTTPException(422, "close_hour must be after open_hour")
    db.commit()
    return attraction_out(a)


@router.delete("/attractions/{slug}")
def delete_attraction(slug: str, db: Session = Depends(get_db)):
    db.delete(_attr(db, slug))
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ users
@router.get("/users")
def users(db: Session = Depends(get_db)):
    rows = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return {"items": [{"id": u.id, "email": u.email, "name": u.name, "role": u.role, "is_active": u.is_active,
                       "created_at": u.created_at.isoformat()} for u in rows]}


@router.patch("/users/{uid}")
def patch_user(uid: int, body: UserPatch, me: User = Depends(admin_user), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == me.id and (body.role == "traveller" or body.is_active is False):
        raise HTTPException(422, "You cannot remove your own admin access")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    db.commit()
    return {"id": u.id, "role": u.role, "is_active": u.is_active}


# ------------------------------------------------------------------ reviews & reports
@router.get("/reviews")
def admin_reviews(status: str | None = Query(None, pattern="^(visible|hidden)$"),
                  source: str | None = Query(None, pattern="^(user|demo)$"), db: Session = Depends(get_db)):
    stmt = select(Review)
    if status:
        stmt = stmt.where(Review.status == status)
    if source:
        stmt = stmt.where(Review.source == source)
    rows = db.scalars(stmt.order_by(Review.created_at.desc(), Review.id.desc()).limit(200)).all()
    return {"items": [{"id": r.id, "destination": r.destination_id, "rating": r.rating, "text": r.text,
                       "sentiment": r.sentiment, "source": r.source, "status": r.status,
                       "author": r.user.name if r.user else "Demo review", "created_at": r.created_at.isoformat()}
                      for r in rows]}


@router.patch("/reviews/{rid}")
def patch_review(rid: int, body: StatusPatch, db: Session = Depends(get_db)):
    r = db.get(Review, rid)
    if not r:
        raise HTTPException(404, "Review not found")
    r.status = body.status
    db.commit()
    return {"id": r.id, "status": r.status}


TARGETS = {"post": Post, "comment": Comment, "review": Review}


def _target_preview(db: Session, r: ContentReport) -> str | None:
    t = db.get(TARGETS[r.target_type], r.target_id)
    if t is None:
        return None
    return (getattr(t, "title", None) or getattr(t, "body", None) or getattr(t, "text", ""))[:200]


@router.get("/content-reports")
def content_reports(status: str = Query("open", pattern="^(open|actioned|dismissed|all)$"), db: Session = Depends(get_db)):
    stmt = select(ContentReport)
    if status != "all":
        stmt = stmt.where(ContentReport.status == status)
    rows = db.scalars(stmt.order_by(ContentReport.created_at.desc())).all()
    return {"items": [{"id": r.id, "target_type": r.target_type, "target_id": r.target_id, "reason": r.reason,
                       "status": r.status, "reporter": r.reporter.name, "preview": _target_preview(db, r),
                       "created_at": r.created_at.isoformat()} for r in rows]}


@router.patch("/content-reports/{rid}")
def patch_report(rid: int, body: ReportPatch, db: Session = Depends(get_db)):
    r = db.get(ContentReport, rid)
    if not r:
        raise HTTPException(404, "Report not found")
    r.status = body.status
    if body.hide_target:
        t = db.get(TARGETS[r.target_type], r.target_id)
        if t is not None:
            t.status = "hidden"
    db.commit()
    return {"id": r.id, "status": r.status}


# ------------------------------------------------------------------ listings
def listing_out(l: Listing) -> dict:
    return {"id": l.id, "destination": l.destination.slug, "name": l.name, "kind": l.kind, "description": l.description,
            "price_band": l.price_band, "contact": l.contact, "verified": l.verified, "source": l.source,
            "updated_at": l.updated_at.isoformat()}


@router.get("/listings")
def listings(destination: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Listing).join(Destination)
    if destination:
        stmt = stmt.where(Destination.slug == destination)
    return {"items": [listing_out(l) for l in db.scalars(stmt.order_by(Destination.name, Listing.name)).all()]}


@router.post("/listings", status_code=201)
def create_listing(body: ListingIn, db: Session = Depends(get_db)):
    d = get_dest(db, body.destination)
    l = Listing(**body.model_dump(exclude={"destination"}), destination_id=d.id, source="admin")
    db.add(l)
    db.commit()
    return listing_out(l)


def _listing(db, lid) -> Listing:
    l = db.get(Listing, lid)
    if not l:
        raise HTTPException(404, "Listing not found")
    return l


@router.put("/listings/{lid}")
def update_listing(lid: int, body: ListingPatch, db: Session = Depends(get_db)):
    l = _listing(db, lid)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(l, k, v)
    db.commit()
    return listing_out(l)


@router.delete("/listings/{lid}")
def delete_listing(lid: int, db: Session = Depends(get_db)):
    db.delete(_listing(db, lid))
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ data sources & system
@router.get("/data-sources")
def data_sources(db: Session = Depends(get_db)):
    return {"items": [{"key": s.key, "name": s.name, "kind": s.kind, "enabled": s.enabled, "description": s.description,
                       "last_updated": s.last_updated.isoformat() if s.last_updated else None}
                      for s in db.scalars(select(DataSource).order_by(DataSource.kind, DataSource.name)).all()]}


@router.patch("/data-sources/{key}")
def patch_source(key: str, body: DataSourcePatch, db: Session = Depends(get_db)):
    s = db.scalar(select(DataSource).where(DataSource.key == key))
    if not s:
        raise HTTPException(404, "Data source not found")
    s.enabled = body.enabled
    db.commit()
    return {"key": s.key, "enabled": s.enabled}


@router.get("/system")
def system(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = "ok"
    except Exception:
        db_ok = "error"
    info = runtime.model().info
    return {"database": db_ok, "database_engine": settings.database_url.split(":", 1)[0],
            "environment": settings.env, "weather_provider": settings.weather_provider,
            "llm_configured": bool(settings.anthropic_api_key), "uptime_seconds": int(time.time() - STARTED),
            "server_time": dt.datetime.now().isoformat(timespec="seconds"),
            "model": {k: info.get(k) for k in ("backend", "trained_at", "history_days", "attractions", "split", "rows",
                                               "test_metrics", "baselines", "uncertainty", "top_features", "note")},
            "levels": {"standard": crowd.STANDARD_T, "sensitive": crowd.SENSITIVE_T}}
