"""Train (or retrain) the crowd model and save it to MODEL_DIR.

Usage (from backend/):  python -m scripts.train_model [--days 365]
Uses the attraction catalogue from the database (seeding it first if empty).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import Attraction
from app.services import runtime, seed
from app.services.forecast import CrowdModel


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=365)
    args = ap.parse_args()
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed.seed_catalogue(db)
        specs = [runtime.spec(a) for a in db.scalars(select(Attraction).options(selectinload(Attraction.destination)))]
    m = CrowdModel()
    info = m.train(specs, end_date=dt.date.today(), days=args.days)
    m.save(settings.model_dir)
    print(json.dumps({k: info[k] for k in ("attractions", "rows", "split", "test_metrics", "baselines", "seconds")}, indent=2))


if __name__ == "__main__":
    main()
