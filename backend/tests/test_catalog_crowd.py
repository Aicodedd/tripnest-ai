"""EPIC-003 Discovery and EPIC-004 Crowd intelligence through the API."""


def test_all_36_states_and_uts_are_present(client):
    states = client.get("/api/states").json()["items"]
    assert len(states) == 36
    assert {s["kind"] for s in states} == {"state", "ut"}
    assert all(s["destinations"] >= 1 for s in states)


def test_search_destinations_by_text(client):
    items = client.get("/api/destinations", params={"q": "taj"}).json()["items"]
    assert [d["slug"] for d in items] == ["agra"]  # matches attraction names too


def test_filter_destinations_by_state_category_and_budget(client):
    items = client.get("/api/destinations", params={"state": "TN"}).json()["items"]
    assert items and all(d["state"]["code"] == "TN" for d in items)
    beach_low = client.get("/api/destinations", params={"category": "beach", "budget": "low"}).json()["items"]
    assert beach_low and all("beach" in d["categories"] and d["budget"] == "low" for d in beach_low)


def test_destination_listing_is_paginated(client):
    r = client.get("/api/destinations", params={"limit": 5, "page": 2}).json()
    assert len(r["items"]) == 5 and r["total"] >= 45 and r["page"] == 2


def test_destination_detail_includes_attractions_and_provenance(client):
    d = client.get("/api/destinations/jaipur").json()
    assert d["name"] == "Jaipur" and d["state"]["name"] == "Rajasthan"
    assert any(a["slug"] == "jaipur-amber-amer-fort" for a in d["attractions"])
    assert d["provenance"]["catalogue"]["kind"] == "catalogue"
    assert "indicative" in d["provenance"]["catalogue"]["note"].lower()


def test_unknown_destination_is_404(client):
    assert client.get("/api/destinations/atlantis").status_code == 404


def test_attraction_forecast_is_labelled_as_demonstration_model_output(client):
    r = client.get("/api/attractions/agra-taj-mahal/forecast", params={"date": "2026-11-14"})
    assert r.status_code == 200
    f = r.json()
    assert len(f["hourly"]) == 13 and f["peak"]["level"] in ("Low", "Moderate", "High", "At Capacity")
    p = f["provenance"]
    assert p["type"] == "model-predicted" and p["training_data"] == "demonstration"
    assert p["generated_at"] and p["model_trained_at"]
    assert len(f["best_times"]) == 5
    assert f["capacity"]["assumed"] is True


def test_destination_crowd_now_lists_every_attraction(client):
    r = client.get("/api/destinations/goa/crowd", params={"at": "2026-11-14T16:00"}).json()
    assert len(r["attractions"]) == 6
    for a in r["attractions"]:
        assert a["level"] in ("Low", "Moderate", "High", "At Capacity", "Closed")
    assert r["overall"]["level"] in ("Low", "Moderate", "High", "At Capacity")


def test_weekend_afternoon_is_busier_than_weekday_morning(client):
    sat = client.get("/api/attractions/agra-taj-mahal/forecast", params={"date": "2026-11-14"}).json()["peak"]["util"]
    tue = client.get("/api/attractions/agra-taj-mahal/forecast", params={"date": "2026-11-10"}).json()["peak"]["util"]
    assert sat > tue


def test_historical_pattern_by_weekday_hour_and_month(client):
    h = client.get("/api/attractions/goa-baga-beach/history").json()
    assert len(h["by_weekday"]) == 7 and len(h["by_month"]) == 12
    assert h["provenance"]["type"] == "historical-demonstration"


def test_compare_crowds_between_destinations(client):
    r = client.get("/api/crowd/compare", params={"slugs": "goa,puducherry,daman", "date": "2026-11-14"}).json()
    assert [d["slug"] for d in r["items"]] == ["goa", "puducherry", "daman"]
    assert all(len(d["hourly"]) > 0 and "peak" in d for d in r["items"])


def test_compare_rejects_too_many_destinations(client):
    slugs = ",".join(["goa", "agra", "jaipur", "delhi", "mumbai", "leh"])
    assert client.get("/api/crowd/compare", params={"slugs": slugs}).status_code == 422


def test_crowd_highlights_give_busiest_and_quietest_hour_for_featured_places(client):
    r = client.get("/api/crowd/highlights", params={"date": "2026-11-14", "limit": 8})
    assert r.status_code == 200
    items = r.json()["items"]
    assert 1 <= len(items) <= 8
    for x in items:
        assert x["peak"]["util"] >= x["quietest"]["util"]
        assert x["attraction"] and x["destination"]["slug"] and x["state"]
    assert r.json()["provenance"]["type"] == "model-predicted"

