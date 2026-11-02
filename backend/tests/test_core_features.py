"""The two core features after the scope change (EPIC-001 crowd prediction, EPIC-002 recommendation, EPIC-003 platform)."""
import pytest

LEVELS = ("Low", "Moderate", "High", "At Capacity")
CHENNAI = {"lat": 13.0827, "lon": 80.2707}


# ================================================================== locations (STORY-009)
def test_city_search_finds_chennai_first_with_state_and_coordinates(client):
    r = client.get("/api/locations/search", params={"q": "chen"})
    assert r.status_code == 200
    first = r.json()["items"][0]
    assert first["name"] == "Chennai" and first["state"] == "Tamil Nadu"
    assert 6 <= first["lat"] <= 37.5 and 68 <= first["lon"] <= 98


def test_city_search_needs_two_characters_and_returns_empty_for_no_match(client):
    assert client.get("/api/locations/search", params={"q": "c"}).status_code == 422
    assert client.get("/api/locations/search", params={"q": "zzzzqq"}).json()["items"] == []


def test_gazetteer_covers_many_states_inside_india(client):
    names = [c["name"] for c in client.get("/api/locations/all").json()["items"]]
    states = {c["state"] for c in client.get("/api/locations/all").json()["items"]}
    assert len(names) >= 60 and len(states) >= 25


@pytest.mark.parametrize("text,expected", [("Chennai", "Chennai"), ("  chennai ", "Chennai"), ("Bangalore", "Bengaluru"),
                                            ("bombay", "Mumbai"), ("Delhi", "Delhi")])
def test_manual_location_text_resolves_with_aliases(client, text, expected):
    r = client.get("/api/locations/resolve", params={"q": text})
    assert r.status_code == 200 and r.json()["name"] == expected


def test_unknown_manual_location_gets_a_helpful_error(client):
    r = client.get("/api/locations/resolve", params={"q": "Atlantis"})
    assert r.status_code == 404 and "nearby" in r.json()["detail"].lower()


# ================================================================== recommendations (STORY-005..008)
def rec(client, **kw):
    params = {**CHENNAI, "date": "2026-12-26", "limit": 6}
    params.update(kw)
    return client.get("/api/recommendations", params={k: v for k, v in params.items() if v is not None})


def test_recommendations_return_complete_cards_sorted_by_score(client):
    r = rec(client)
    assert r.status_code == 200, r.text
    body = r.json()
    items = body["items"]
    assert 1 <= len(items) <= 6
    assert [i["score"] for i in items] == sorted((i["score"] for i in items), reverse=True)
    for i in items:
        assert {"slug", "name", "state", "state_code", "lat", "lon", "categories", "description"} <= set(i)
        assert i["crowd"]["level"] in LEVELS and 0 <= i["crowd"]["util"]
        assert i["crowd"]["low"] <= i["crowd"]["visitors"] <= i["crowd"]["high"]
        assert i["suggested_time"]["label"] and i["suggested_time"]["level"] in LEVELS
        assert i["reasons"] and all(isinstance(x, str) for x in i["reasons"])
        assert i["distance_km"] >= 0 and i["distance_note"] == "straight-line distance"
    assert body["provenance"]["type"] == "model-predicted" and body["provenance"]["training_data"] == "demonstration"


def test_score_is_the_weighted_sum_of_the_shown_factors(client):
    body = rec(client, interest="beach").json()
    w = body["weights"]
    assert abs(sum(w.values()) - 1) < 1e-6
    for i in body["items"]:
        expect = sum(w[k] * v for k, v in i["breakdown"].items() if k in w)
        assert i["score"] == pytest.approx(expect, abs=0.002)


def test_popularity_is_not_a_scoring_factor(client):
    assert set(rec(client).json()["weights"]) == {"crowd", "interest", "distance", "season"}


def test_interest_changes_the_ranking_and_is_explained(client):
    items = rec(client, interest="beach").json()["items"]
    assert "beach" in items[0]["categories"]
    assert any("beach" in r.lower() for r in items[0]["reasons"])
    wildlife = rec(client, interest="wildlife").json()["items"]
    assert "wildlife" in wildlife[0]["categories"] and wildlife[0]["slug"] != items[0]["slug"]


def test_without_an_origin_distance_is_dropped_and_weights_renormalise(client):
    body = client.get("/api/recommendations", params={"date": "2026-12-26"}).json()
    assert body["weights"]["distance"] == 0 and abs(sum(body["weights"].values()) - 1) < 1e-6
    assert all(i["distance_km"] is None for i in body["items"])


def test_without_an_interest_that_weight_is_dropped(client):
    assert rec(client).json()["weights"]["interest"] == 0


def test_distance_limit_filters_far_destinations(client):
    items = rec(client, max_km=500, limit=20).json()["items"]
    assert items and all(i["distance_km"] <= 500 for i in items)


def test_busier_dates_lower_the_crowd_score_for_the_same_destination(client):
    def crowd_score(date):
        items = rec(client, interest="beach", date=date, limit=40).json()["items"]
        return next(i for i in items if i["slug"] == "goa")["breakdown"]["crowd"]
    assert crowd_score("2026-12-22") > crowd_score("2026-12-26")  # Tuesday vs Saturday


def test_recommendation_input_validation(client):
    assert client.get("/api/recommendations").status_code == 422                                   # date is required
    assert rec(client, date="26-12-2026").status_code == 422
    assert rec(client, date="2031-01-01").status_code == 422                                       # beyond 18 months
    assert rec(client, lat=95).status_code == 422
    assert client.get("/api/recommendations", params={"lat": 13, "date": "2026-12-26"}).status_code == 422  # lat without lon
    assert rec(client, interest="x" * 40).status_code == 422
    assert rec(client, limit=0).status_code == 422


# ================================================================== destination prediction (STORY-001..004)
def pred(client, slug="goa", **kw):
    params = {"date": "2026-12-26", "from": 9, "to": 17}
    params.update(kw)
    return client.get(f"/api/destinations/{slug}/prediction", params=params)


def test_prediction_for_a_date_and_time_range(client):
    r = pred(client)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["destination"]["slug"] == "goa" and p["destination"]["state"] == "Goa"
    assert p["selected"]["level"] in LEVELS and 9 <= p["selected"]["peak_hour"] <= 17
    s = p["selected"]
    assert s["low"] <= s["visitors"] <= s["high"] and s["from"] == 9 and s["to"] == 17
    assert p["best_time"]["level"] in LEVELS and p["best_time"]["label"]
    assert len(p["hourly"]) >= 8 and all(h["level"] in LEVELS for h in p["hourly"])
    assert [d["date"] for d in p["week"]] == ["2026-12-26", "2026-12-27", "2026-12-28", "2026-12-29", "2026-12-30", "2026-12-31", "2027-01-01"]
    assert all(a["level"] in LEVELS and a["best_hour_label"] for a in p["attractions"])


def test_prediction_states_what_it_is_and_what_it_cannot_do(client):
    p = pred(client).json()["provenance"]
    assert p["type"] == "model-predicted" and p["training_data"] == "demonstration"
    assert p["generated_at"] and p["model_trained_at"] and p["data_freshness"]
    assert len(p["limitations"]) >= 3
    assert any("not live" in x.lower() or "no live" in x.lower() for x in p["limitations"])
    assert p["uncertainty"]["method"] and p["uncertainty"]["confidence"] == 0.8


def test_weekend_is_busier_than_a_weekday_for_the_same_hours(client):
    sat = pred(client, date="2026-12-26").json()["selected"]["avg_util"]
    tue = pred(client, date="2026-12-22").json()["selected"]["avg_util"]
    assert sat > tue


def test_prediction_defaults_and_validation(client):
    assert client.get("/api/destinations/goa/prediction", params={"date": "2026-12-26"}).status_code == 200
    assert pred(client, **{"from": 18, "to": 9}).status_code == 422
    assert pred(client, **{"from": -1}).status_code == 422
    assert pred(client, to=25).status_code == 422
    assert pred(client, date="nope").status_code == 422
    assert pred(client, slug="atlantis").status_code == 404


def test_a_range_outside_opening_hours_gives_a_clear_answer_not_a_crash(client):
    r = pred(client, **{"from": 0, "to": 3})
    assert r.status_code == 200 and r.json()["selected"]["level"] in LEVELS + ("Closed",)


# ================================================================== comparison (STORY-010)
def test_compare_two_to_four_destinations_with_levels(client):
    r = client.get("/api/crowd/compare", params={"slugs": "goa,jaipur,munnar", "date": "2026-12-26"}).json()
    assert [d["slug"] for d in r["items"]] == ["goa", "jaipur", "munnar"]
    assert all(d["peak"]["level"] in LEVELS and d["hourly"] for d in r["items"])


# ================================================================== platform (EPIC-003)
def test_health_reports_database_and_model(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["database"] == "ok" and body["model"]["loaded"] is True


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_model_card_reports_test_metrics_and_baselines(client):
    m = client.get("/api/model").json()
    assert m["test_metrics"]["mape"] < m["baselines"]["seasonal_naive"]["mape"]
    assert m["test_metrics"]["mape"] < m["baselines"]["weekday_hour_mean"]["mape"]
    assert m["data_provenance"] == "demonstration" and m["split"]["train_end"] < m["split"]["test_start"]


@pytest.mark.parametrize("path", ["/api/itineraries", "/api/posts", "/api/admin/stats", "/api/destinations/goa/reviews",
                                  "/api/destinations/goa/weather", "/api/me/profile", "/api/community/guidelines"])
def test_removed_modules_are_not_exposed(client, path):
    assert client.get(path).status_code == 404


def test_api_documentation_lists_only_core_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in paths:
        assert not any(x in p for x in ("itinerar", "posts", "reviews", "/admin", "weather", "/auth", "favourites", "community"))
    assert "/api/recommendations" in paths and "/api/destinations/{slug}/prediction" in paths
