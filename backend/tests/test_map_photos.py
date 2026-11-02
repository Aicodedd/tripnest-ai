"""Crowd heat map data and place photos (STORY-013 map colours, STORY-020 photos)."""
from app.services import photos


def test_crowd_map_returns_every_attraction_with_level_and_heat(client):
    r = client.get("/api/crowd/map", params={"at": "2026-11-14T16:00"})
    assert r.status_code == 200
    body = r.json()
    pts = body["points"]
    assert len(pts) >= 200
    for p in pts:
        assert p["level"] in ("Low", "Moderate", "High", "At Capacity", "Closed")
        assert 0 <= p["heat"] <= 1
        if p["level"] in ("Low", "Closed"):
            assert p["heat"] == 0  # quiet places stay uncoloured on the map
    assert body["provenance"]["type"] == "model-predicted"


def test_crowd_map_can_be_limited_to_one_destination(client):
    pts = client.get("/api/crowd/map", params={"destination": "goa", "at": "2026-11-14T16:00"}).json()["points"]
    assert len(pts) == 6 and all(p["destination"] == "goa" for p in pts)


def test_crowd_heat_is_higher_for_busier_levels():
    assert photos is not None
    from app.routers.catalog import heat_of
    assert heat_of(0.2, "Low") == 0
    assert 0 < heat_of(0.55, "Moderate") < heat_of(0.8, "High") < heat_of(1.0, "At Capacity") <= 1


def test_photo_endpoint_reports_unavailable_when_turned_off(client):
    r = client.get("/api/attractions/agra-taj-mahal/photo")
    assert r.status_code == 200
    assert r.json()["available"] is False and r.json()["reason"]


def test_photo_parser_extracts_image_credit_and_licence():
    page = {"query": {"pages": {"1": {"title": "Taj Mahal", "fullurl": "https://en.wikipedia.org/wiki/Taj_Mahal",
                                      "thumbnail": {"source": "https://upload.wikimedia.org/x/800px-Taj.jpg", "width": 800, "height": 533},
                                      "pageimage": "Taj-Mahal.jpg"}}}}
    meta = {"query": {"pages": {"-1": {"imageinfo": [{"descriptionurl": "https://commons.wikimedia.org/wiki/File:Taj-Mahal.jpg",
                                                      "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 4.0"},
                                                                      "Artist": {"value": "<a href='x'>Jane Doe</a>"}}}]}}}}
    out = photos.parse(page, meta)
    assert out["available"] is True
    assert out["url"].startswith("https://upload.wikimedia.org/")
    assert out["credit"] == "Jane Doe" and out["licence"] == "CC BY-SA 4.0"
    assert out["source_page"].startswith("https://commons.wikimedia.org/")
    assert out["article"] == "https://en.wikipedia.org/wiki/Taj_Mahal"


def test_photo_parser_rejects_non_wikimedia_or_missing_images():
    assert photos.parse({"query": {"pages": {"1": {"title": "X"}}}}, None)["available"] is False
    bad = {"query": {"pages": {"1": {"title": "X", "thumbnail": {"source": "http://evil.example/x.jpg"}, "pageimage": "x.jpg"}}}}
    assert photos.parse(bad, None)["available"] is False


def test_photo_parser_accepts_wikimedia_thumb_host_and_strips_tracking():
    page = {"query": {"pages": {"1": {"title": "Taj Mahal", "index": 1, "pageimage": "T.jpeg",
            "thumbnail": {"source": "https://thumb.wikimedia.org/wikipedia/commons/thumb/1/1d/T.jpeg/800px-T.jpeg?utm_source=en.wikipedia.org"}}}}}
    out = photos.parse(page, None)
    assert out["available"] and out["url"] == "https://thumb.wikimedia.org/wikipedia/commons/thumb/1/1d/T.jpeg/800px-T.jpeg"


def test_batched_day_forecasts_match_single_forecasts(client):
    import datetime as dt
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db import SessionLocal
    from app.models import Attraction
    from app.services import crowd, runtime
    with SessionLocal() as db:
        specs = [runtime.spec(a) for a in db.scalars(select(Attraction).options(selectinload(Attraction.destination)).limit(12))]
    d = dt.date(2026, 12, 19)
    runtime._cache.clear()
    runtime.prefetch_day(specs, d)
    assert all(runtime._cache_key(s, d) in runtime._cache for s in specs)
    for s in specs[:3]:
        assert runtime.day_forecast(s, d) == crowd.day_forecast(runtime.model(), s, d)
