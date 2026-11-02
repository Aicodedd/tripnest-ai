"""Idempotent seeding: states, destinations and attractions (adding only what is missing), destination photos,
the data-source registry and an optional first account. Existing rows are never changed or deleted."""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..data import catalog
from ..data.catalog_extra import EXTRA_DESTINATIONS
from ..models import Attraction, DataSource, Destination, State, User
from ..security import hash_password

log = logging.getLogger("tripnest.seed")
IMAGES_FILE = Path(__file__).resolve().parent.parent / "data" / "images.json"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def seed_catalogue(db: Session) -> int:
    """Create missing states, destinations and attractions. Returns the number of destinations added."""
    states = {s.code: s for s in db.scalars(select(State)).all()}
    for code, name, kind, region in catalog.STATES:
        if code not in states:
            s = State(code=code, name=name, kind=kind, region=region)
            db.add(s)
            states[code] = s
    db.flush()
    have = set(db.scalars(select(Destination.slug)).all())
    added = 0
    for (slug, name, st, lat, lon, cats, budget, cost, min_days, months, climate, featured, pop, desc, reach,
         attrs) in [*catalog.DESTINATIONS, *EXTRA_DESTINATIONS]:
        if slug in have:
            continue
        d = Destination(slug=slug, name=name, state=states[st], lat=lat, lon=lon, categories=cats, budget=budget,
                        daily_cost=cost, min_days=min_days, best_months=months, climate=climate, featured=featured,
                        popularity=pop, description=desc, how_to_reach=reach,
                        facilities=["Hotels and homestays", "Restaurants", "ATMs", "Local taxis"])
        db.add(d)
        for (aname, cat, alat, alon, cap, apop, op, cl, fee, flags, vmin, tags) in attrs:
            db.add(Attraction(slug=f"{slug}-{slugify(aname)}", destination=d, name=aname, category=cat, lat=alat,
                              lon=alon, capacity=cap, popularity=apop, open_hour=op, close_hour=cl, fee=fee,
                              sensitive="S" in flags, covered="C" in flags, family_friendly="K" not in flags,
                              elder_friendly="E" not in flags, visit_min=vmin, tags=tags,
                              description=f"{cat.capitalize()} in {name}. Hours and fee are indicative."))
        added += 1
    if not db.scalar(select(DataSource.id).limit(1)):
        for key, name, kind, desc in catalog.DATA_SOURCES:
            db.add(DataSource(key=key, name=name, kind=kind, description=desc, last_updated=dt.datetime(2026, 11, 1)))
    db.commit()
    if added:
        log.info("catalogue: %d destination(s) added", added)
    return added


def apply_images(db: Session) -> int:
    """Fill destination photo columns from data/images.json (written by scripts/fetch_images.py). Fills empty ones only."""
    if not IMAGES_FILE.exists():
        return 0
    data = json.loads(IMAGES_FILE.read_text())
    n = 0
    for d in db.scalars(select(Destination).where(Destination.image_url.is_(None))).all():
        im = data.get(d.slug)
        if im:
            d.image_url, d.image_title, d.image_credit = im["url"], im.get("title"), im.get("credit")
            d.image_licence, d.image_source_page = im.get("licence"), im.get("source_page")
            n += 1
    db.commit()
    return n


def ensure_admin(db: Session) -> None:
    """Legacy: create an account from ADMIN_EMAIL / ADMIN_PASSWORD if both are set. The product has no accounts."""
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    pw = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not pw or db.scalar(select(User).where(User.email == email)):
        return
    db.add(User(email=email, name="Administrator", password_hash=hash_password(pw), role="admin"))
    db.commit()


def run(db: Session) -> None:
    seed_catalogue(db)
    apply_images(db)
    ensure_admin(db)
