"""Location-first discovery: nearest city, popular places, hidden gems, time-of-day timeline, best window, map data."""
import re

import pytest

from app.services import prediction

LEVELS = ("Low", "Moderate", "High", "At Capacity")
COIMBATORE = {"lat": 11.0168, "lon": 76.9558}
GREEN_YELLOW_RED = {"Low": "green", "Moderate": "yellow", "High": "red", "At Capacity": "red"}


# ================================================================== nearest city (greeting)
def test_nearest_city_names_the_resolved_location(client):
    r = client.get("/api/locations/nearest", params=COIMBATORE).json()
    assert r["name"] == "Coimbatore" and r["label"] == "Coimbatore" and r["covered"] is True and r["distance_km"] < 5


def test_a_position_between_cities_is_described_as_near_one(client):
    r = client.get("/api/locations/nearest", params={"lat": 10.65, "lon": 77.0}).json()
    assert r["label"] == "near Coimbatore" and 20 < r["distance_km"] < 80


def test_a_position_outside_india_is_not_covered(client):
    r = client.get("/api/locations/nearest", params={"lat": 51.5, "lon": -0.12}).json()
    assert r["covered"] is False and "India" in r["message"]


def test_nearest_city_validates_coordinates(client):
    assert client.get("/api/locations/nearest", params={"lat": 95, "lon": 10}).status_code == 422
    assert client.get("/api/locations/nearest", params={"lat": 10}).status_code == 422


# ================================================================== timeline and best window (unit)
def hours(profile, start=5):
    """profile: utilisation per hour starting at `start`."""
    return [{"hour": start + i, "label": prediction.hour_label(start + i), "util": u, "visitors": int(u * 1000), "low": int(u * 800),
             "high": int(u * 1200), "level": prediction.crowd.level_of(u, False)} for i, u in enumerate(profile)]


def test_timeline_has_four_slots_and_flags_the_calmest_available_one():
    h = hours([0.20, 0.25, 0.35, 0.55, 0.75, 0.95, 0.9, 0.8, 0.6, 0.5, 0.6, 0.8, 0.7, 0.4, 0.3])   # 5 AM .. 7 PM
    t = prediction.timeline(h)
    assert [s["label"] for s in t] == ["Early morning", "Morning", "Afternoon", "Evening"]
    assert [s["range"] for s in t] == ["5–8 AM", "8 AM–12 PM", "12–4 PM", "4–8 PM"]
    assert all(s["available"] and s["level"] in LEVELS for s in t)
    assert [s["best"] for s in t] == [True, False, False, False]
    assert t[1]["level"] == "At Capacity" and t[2]["level"] == "High"                                 # 0.95 at 10 AM; 0.8 at noon


def test_slots_with_no_open_hours_are_unavailable_and_never_best():
    t = prediction.timeline(hours([0.5, 0.4, 0.3, 0.3, 0.4, 0.6, 0.5, 0.5], start=9))               # open 9 AM - 5 PM
    assert t[0]["available"] is False and t[0]["level"] == "Closed" and t[0]["best"] is False
    assert any(s["best"] for s in t if s["available"])


def test_best_window_is_the_calmest_hour_with_a_plain_message():
    w = prediction.best_window(hours([0.45, 0.30, 0.15, 0.35, 0.6, 0.9, 0.85, 0.7, 0.6, 0.5, 0.45, 0.5, 0.4, 0.3, 0.25]))
    assert w["available"] is True and w["label"] == "7:00 AM – 8:00 AM" and w["start_hour"] == 7 and w["level"] == "Low"
    assert "lower" in w["message"].lower() and "predicted" in w["message"].lower()


def test_no_time_is_recommended_when_crowds_stay_high_all_day():
    w = prediction.best_window(hours([0.8, 0.85, 0.9, 0.95, 1.0, 1.0, 0.95, 0.9, 0.9, 0.95, 0.9, 0.85, 0.8, 0.75, 0.75]))
    assert w["available"] is False and "high" in w["message"].lower() and "another date" in w["message"].lower()


def test_no_time_is_recommended_without_enough_opening_hours():
    w = prediction.best_window(hours([0.2, 0.3], start=9))
    assert w["available"] is False and "opening hours" in w["message"].lower()


# ================================================================== explore (popular + hidden gems + map)
def explore(client, **kw):
    params = {**COIMBATORE, "date": "2026-12-26"}
    params.update(kw)
    return client.get("/api/explore", params={k: v for k, v in params.items() if v is not None})


def test_explore_returns_popular_places_and_hidden_gems_around_a_location(client):
    r = explore(client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["origin"]["label"] == "Coimbatore" and body["origin"]["covered"] is True
    pop, gems = body["popular"], body["hidden_gems"]
    assert 3 <= len(pop) <= 6 and 3 <= len(gems) <= 6
    assert all(p["group"] == "popular" and p["popularity"] >= 0.9 for p in pop)
    assert all(g["group"] == "hidden_gem" and g["popularity"] <= 0.8 for g in gems)
    assert [p["distance_km"] for p in pop] == sorted(p["distance_km"] for p in pop)                 # nearest first
    assert {p["slug"] for p in pop}.isdisjoint({g["slug"] for g in gems})
    assert body["classification"]["popular_min"] == 0.9 and body["classification"]["gem_max"] == 0.8
    assert body["provenance"]["type"] == "model-predicted" and body["provenance"]["training_data"] == "demonstration"


def test_every_card_has_photo_crowd_colour_timeline_and_best_time(client):
    body = explore(client).json()
    for it in body["popular"] + body["hidden_gems"]:
        assert it["image"]["url"].startswith("https://") and it["image"]["credit"] and it["image"]["licence"]
        assert it["crowd"]["level"] in LEVELS and it["crowd_display"]["color"] == GREEN_YELLOW_RED[it["crowd"]["level"]]
        assert len(it["timeline"]) == 4 and sum(s["best"] for s in it["timeline"]) <= 1
        bw = it["best_window"]
        assert isinstance(bw["available"], bool) and bw["message"]
        if bw["available"]:
            assert re.fullmatch(r"\d{1,2}:00 (AM|PM) – \d{1,2}:00 (AM|PM)", bw["label"]) and bw["level"] in ("Low", "Moderate")
        assert it["description"] and it["state"] and it["reasons"]


def test_hidden_gems_are_justified_calmer_and_explained(client):
    body = explore(client).json()
    for g in body["hidden_gems"]:
        assert "lesser-known" in g["classification_reason"].lower() and str(g["popularity"]) in g["classification_reason"]
        assert g["crowd"]["level"] in ("Low", "Moderate")
        assert any("calm" in r.lower() or "quiet" in r.lower() or "lower" in r.lower() for r in g["reasons"])
    assert any(g.get("alternative_to") for g in body["hidden_gems"])
    alt = next(g["alternative_to"] for g in body["hidden_gems"] if g.get("alternative_to"))
    assert alt["slug"] and alt["name"] and alt["level"] in LEVELS


def test_map_points_cover_both_groups_with_colours_and_distances(client):
    body = explore(client).json()
    pts = {p["slug"]: p for p in body["map"]}
    for it in body["popular"] + body["hidden_gems"]:
        assert pts[it["slug"]]["group"] == it["group"]
    for p in body["map"]:
        assert p["color"] in ("green", "yellow", "red") and p["level"] in LEVELS and p["distance_km"] >= 0
        assert p["image_url"] and p["blurb"] and p["best_label"]
        assert p["group"] in ("popular", "hidden_gem", "other")


def test_a_busy_lesser_known_place_is_never_drawn_as_a_hidden_gem_on_the_map(client):
    body = explore(client).json()
    shown = {g["slug"] for g in body["hidden_gems"]}
    gem_points = [p for p in body["map"] if p["group"] == "hidden_gem"]
    assert {p["slug"] for p in gem_points} == shown
    assert all(p["level"] in ("Low", "Moderate") for p in gem_points)
    assert any(p["group"] == "other" for p in body["map"])


def test_time_slot_changes_the_crowd_reading(client):
    allday = explore(client, date="2026-12-26").json()["popular"]
    early = explore(client, date="2026-12-26", slot="early").json()["popular"]
    assert all(e["crowd"]["slot"] == "early" for e in early) and all(a["crowd"]["slot"] == "all" for a in allday)
    by = {a["slug"]: a for a in allday}
    assert any(e["crowd"]["util"] < by[e["slug"]]["crowd"]["util"] for e in early if e["slug"] in by)
    assert explore(client, slot="midnight").status_code == 422


def test_changing_the_date_changes_the_predictions(client):
    near_goa = {"lat": 15.4909, "lon": 73.8278}
    sat = {p["slug"]: p for p in explore(client, **near_goa, date="2026-12-26").json()["popular"]}
    tue = {p["slug"]: p for p in explore(client, **near_goa, date="2026-12-22").json()["popular"]}
    assert sat["goa"]["crowd"]["util"] > tue["goa"]["crowd"]["util"]


def test_interest_puts_matching_places_first(client):
    items = explore(client, lat=15.4909, lon=73.8278, interest="beach").json()["popular"]
    assert "beach" in items[0]["categories"]


def test_remote_origin_expands_to_the_nearest_places_and_says_so(client):
    body = explore(client, lat=11.6234, lon=92.7265).json()                                         # Port Blair
    assert body["popular"] and body["popular_expanded"] is True
    assert "nearest" in body["popular_note"].lower()


def test_origin_outside_india_returns_a_clear_message_not_results(client):
    body = explore(client, lat=51.5, lon=-0.12).json()
    assert body["origin"]["covered"] is False and body["popular"] == [] and body["hidden_gems"] == []
    assert "India" in body["message"]


def test_explore_validation(client):
    assert client.get("/api/explore", params=COIMBATORE).status_code == 422                          # date required
    assert client.get("/api/explore", params={"lat": 11, "date": "2026-12-26"}).status_code == 422   # lat needs lon
    assert client.get("/api/explore", params={"date": "2026-12-26"}).status_code == 422              # a location is required
    assert explore(client, date="2031-01-01").status_code == 422
    assert explore(client, interest="x" * 40).status_code == 422


# ================================================================== details
def test_prediction_includes_timeline_best_window_and_stored_photo(client):
    p = client.get("/api/destinations/munnar/prediction", params={"date": "2026-12-26"}).json()
    assert len(p["timeline"]) == 4 and "available" in p["best_window"]
    assert p["destination"]["image"]["url"].startswith("https://") and p["destination"]["image"]["licence"]


def test_destination_card_carries_the_stored_photo_and_credit(client):
    d = client.get("/api/destinations/agra").json()
    assert d["image"]["url"] and d["image"]["credit"] and d["image"]["source_page"].startswith("https://commons.wikimedia.org/")


def test_catalogue_now_has_many_lesser_known_destinations(client):
    assert client.get("/api/destinations", params={"limit": 1}).json()["total"] >= 80
    assert client.get("/api/destinations/valparai").status_code == 200


@pytest.mark.parametrize("slug", ["lonavala", "panchgani", "alibag", "valparai", "gokarna"])
def test_new_destinations_get_forecasts_without_retraining(client, slug):
    p = client.get(f"/api/destinations/{slug}/prediction", params={"date": "2026-12-26"})
    assert p.status_code == 200 and p.json()["selected"]["level"] in LEVELS + ("Closed",)
