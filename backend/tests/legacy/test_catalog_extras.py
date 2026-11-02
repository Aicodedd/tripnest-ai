"""Legacy: tests for features outside the current scope (crowd reports, weather). Not collected."""


def test_logged_in_crowd_report_shifts_live_estimate(user_client):
    at = "2026-11-10T09:00"
    before = user_client.get("/api/destinations/kohima/crowd", params={"at": at}).json()
    a0 = next(a for a in before["attractions"] if a["slug"] == "kohima-kohima-war-cemetery")
    for _ in range(3):
        r = user_client.post("/api/attractions/kohima-kohima-war-cemetery/reports", json={"level": "packed", "at": at})
        assert r.status_code == 201
    after = user_client.get("/api/destinations/kohima/crowd", params={"at": at}).json()
    a1 = next(a for a in after["attractions"] if a["slug"] == "kohima-kohima-war-cemetery")
    assert a1["util"] > a0["util"] and a1["reports"] == 3


def test_anonymous_crowd_report_is_refused(fresh_client):
    fresh_client.headers.update({"X-Requested-With": "TripNest"})
    r = fresh_client.post("/api/attractions/agra-taj-mahal/reports", json={"level": "low"})
    assert r.status_code == 401


def test_model_card_reports_test_metrics_and_baselines(client):
    m = client.get("/api/model").json()
    assert m["test_metrics"]["mape"] < m["baselines"]["seasonal_naive"]["mape"]
    assert m["data_provenance"] == "demonstration"


def test_weather_unavailable_state_is_explicit(client):
    w = client.get("/api/destinations/goa/weather").json()
    assert w["available"] is False and w["reason"]
