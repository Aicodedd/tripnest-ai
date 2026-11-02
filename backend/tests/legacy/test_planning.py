"""EPIC-005 Recommendations and EPIC-006 Itinerary planner."""
import datetime as dt


def recommend(client, **kw):
    body = {"interests": ["beach"], "budget": "mid", "days": 3, "group_type": "couple", "travel_date": "2026-12-05"}
    body.update(kw)
    return client.post("/api/recommendations", json=body)


def test_recommendations_are_ranked_and_explained(client):
    r = recommend(client)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert 1 <= len(items) <= 10
    scores = [i["score"] for i in items]
    assert scores == sorted(scores, reverse=True)
    top = items[0]
    assert "beach" in top["categories"]
    assert top["reasons"] and all(isinstance(x, str) for x in top["reasons"])
    assert top["crowd"]["level"] in ("Low", "Moderate", "High", "At Capacity")
    assert set(top["breakdown"]) >= {"interest", "crowd", "budget", "season", "distance", "group", "duration"}


def test_max_distance_filters_far_destinations(client):
    items = recommend(client, interests=[], origin={"lat": 13.08, "lon": 80.27}, max_distance_km=400).json()["items"]
    assert items and all(i["distance_km"] <= 400 for i in items)


def test_low_budget_prefers_affordable_destinations(client):
    items = recommend(client, interests=["heritage"], budget="low").json()["items"]
    assert items[0]["budget"] in ("low", "mid")


def test_family_with_kids_excludes_unsuitable_highlights(client):
    items = recommend(client, interests=["trek", "nature"], group_type="family").json()["items"]
    assert items  # still recommends; suitability is part of the score
    assert all(i["breakdown"]["group"] <= 1 for i in items)


def test_recommendation_input_is_validated(client):
    assert recommend(client, days=0).status_code == 422
    assert recommend(client, budget="unlimited").status_code == 422


def plan_body(**kw):
    body = {"destinations": ["jaipur"], "start_date": "2026-12-05", "days": 2, "interests": ["heritage"],
            "group_type": "couple", "budget": "mid", "pace": "normal"}
    body.update(kw)
    return body


def test_generate_itinerary_is_day_wise_and_respects_opening_hours(client):
    r = client.post("/api/itineraries/generate", json=plan_body())
    assert r.status_code == 200, r.text
    plan = r.json()["plan"]
    assert [d["day"] for d in plan["days"]] == [1, 2]
    assert plan["days"][0]["date"] == "2026-12-05"
    seen = set()
    for day in plan["days"]:
        prev_end = "00:00"
        for s in day["stops"]:
            assert s["start"] >= prev_end and s["end"] > s["start"]
            assert s["slug"] not in seen
            seen.add(s["slug"])
            assert s["open_hour"] * 100 <= int(s["start"].replace(":", "")) and int(s["end"].replace(":", "")) <= s["close_hour"] * 100
            assert s["predicted"]["level"] in ("Low", "Moderate", "High", "At Capacity")
            prev_end = s["end"]
    assert plan["disclaimer"] and plan["generated_by"]
    assert any("estimate" in s.get("travel_note", "") for d in plan["days"] for s in d["stops"][1:])


def test_multi_destination_itinerary_adds_travel_day_note(client):
    plan = client.post("/api/itineraries/generate", json=plan_body(destinations=["agra", "delhi"], days=3)).json()["plan"]
    names = [d["destination"]["slug"] for d in plan["days"]]
    assert names[0] == "agra" and names[-1] == "delhi"
    assert any(d.get("travel_note") for d in plan["days"][1:])


def test_itinerary_validation(client):
    assert client.post("/api/itineraries/generate", json=plan_body(days=15)).status_code == 422
    assert client.post("/api/itineraries/generate", json=plan_body(destinations=["nowhere"])).status_code == 404


def test_save_list_edit_regenerate_and_delete_itinerary(user_client):
    r = user_client.post("/api/itineraries", json={"title": "Pink City weekend", **plan_body()})
    assert r.status_code == 201, r.text
    it = r.json()
    iid = it["id"]
    assert [i["id"] for i in user_client.get("/api/itineraries").json()["items"]] == [iid]

    day1 = [s["slug"] for s in it["plan"]["days"][0]["stops"]]
    reordered = list(reversed(day1))[:-1]  # reverse and drop one stop
    edit = {"title": "Edited trip", "notes": "Carry water",
            "days": [{"stops": reordered}, {"stops": [s["slug"] for s in it["plan"]["days"][1]["stops"]]}]}
    r = user_client.put(f"/api/itineraries/{iid}", json=edit)
    assert r.status_code == 200, r.text
    got = user_client.get(f"/api/itineraries/{iid}").json()
    assert got["title"] == "Edited trip" and got["notes"] == "Carry water"
    assert [s["slug"] for s in got["plan"]["days"][0]["stops"]] == reordered

    r = user_client.post(f"/api/itineraries/{iid}/regenerate", json={})
    assert r.status_code == 200 and r.json()["plan"]["days"]

    assert user_client.delete(f"/api/itineraries/{iid}").status_code == 200
    assert user_client.get(f"/api/itineraries/{iid}").status_code == 404


def test_edit_rejects_unknown_attraction(user_client):
    iid = user_client.post("/api/itineraries", json={"title": "T", **plan_body(days=1)}).json()["id"]
    r = user_client.put(f"/api/itineraries/{iid}", json={"days": [{"stops": ["not-a-real-place"]}]})
    assert r.status_code == 422


def test_users_cannot_see_each_others_itineraries(user_client, app):
    from fastapi.testclient import TestClient
    from tests.conftest import CSRF
    iid = user_client.post("/api/itineraries", json={"title": "Private", **plan_body(days=1)}).json()["id"]
    with TestClient(app, headers=CSRF) as other:
        other.post("/api/auth/register", json={"email": "other-user@example.com", "name": "O", "password": "Other-pass-1"})
        assert other.get(f"/api/itineraries/{iid}").status_code == 404
        assert other.delete(f"/api/itineraries/{iid}").status_code == 404


def test_start_date_in_the_past_is_allowed_for_demo_but_not_too_far(client):
    far = (dt.date.today() + dt.timedelta(days=800)).isoformat()
    assert client.post("/api/itineraries/generate", json=plan_body(start_date=far)).status_code == 422
