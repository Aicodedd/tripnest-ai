"""EPIC-007 Reviews & sentiment, EPIC-008 Community, EPIC-009 Administration, EPIC-010 Platform security."""
from app.services import sentiment


# ---------------------------------------------------------------- sentiment unit tests
def test_sentiment_detects_negative_aspects():
    r = sentiment.analyze("The toilets were dirty and the parking was a nightmare.")
    assert r["label"] == "negative"
    neg = {a["aspect"] for a in r["aspects"] if a["sentiment"] == "negative"}
    assert {"cleanliness", "parking"} <= neg


def test_sentiment_handles_negation_and_positive_text():
    assert sentiment.analyze("Not crowded at all, very peaceful and clean.")["label"] == "positive"
    assert sentiment.analyze("The staff were not helpful.")["label"] == "negative"


# ---------------------------------------------------------------- reviews API
def test_submit_review_is_analysed_and_listed(user_client):
    r = user_client.post("/api/destinations/hampi/reviews",
                         json={"rating": 2, "text": "Stunning ruins but the queue was very long and toilets were dirty."})
    assert r.status_code == 201, r.text
    assert r.json()["sentiment"] in ("negative", "neutral")
    data = user_client.get("/api/destinations/hampi/reviews").json()
    mine = [x for x in data["items"] if x["source"] == "user"]
    assert mine and mine[0]["author"] == "Test Traveller"
    s = data["summary"]
    assert s["count"] >= 1 and set(s["sentiment"]) == {"positive", "neutral", "negative"}
    assert any(t["aspect"] == "cleanliness" for t in s["complaints"])


def test_demo_reviews_are_labelled(client):
    items = client.get("/api/destinations/goa/reviews").json()["items"]
    demo = [x for x in items if x["source"] == "demo"]
    assert demo and all(x["author"] == "Demo review" for x in demo)


def test_review_validation_and_auth(user_client, fresh_client):
    assert user_client.post("/api/destinations/hampi/reviews", json={"rating": 6, "text": "Great place to visit"}).status_code == 422
    assert user_client.post("/api/destinations/hampi/reviews", json={"rating": 4, "text": "ok"}).status_code == 422
    fresh_client.headers.update({"X-Requested-With": "TripNest"})
    assert fresh_client.post("/api/destinations/hampi/reviews", json={"rating": 4, "text": "Lovely sunset views"}).status_code == 401


# ---------------------------------------------------------------- community
def test_post_comment_and_report_flow(user_client):
    r = user_client.post("/api/posts", json={"title": "Quiet morning at Hampi", "body": "Go before 8 AM <script>x</script>",
                                             "destination": "hampi"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert user_client.post(f"/api/posts/{pid}/comments", json={"body": "Thanks for the tip!"}).status_code == 201
    post = user_client.get(f"/api/posts/{pid}").json()
    assert post["body"].startswith("Go before 8 AM") and len(post["comments"]) == 1
    assert any(p["id"] == pid for p in user_client.get("/api/posts").json()["items"])
    r = user_client.post("/api/content-reports", json={"target_type": "post", "target_id": pid, "reason": "Spam link"})
    assert r.status_code == 201


def test_report_requires_existing_target(user_client):
    r = user_client.post("/api/content-reports", json={"target_type": "post", "target_id": 999999, "reason": "x spam"})
    assert r.status_code == 404


def test_only_author_can_delete_post(user_client, app):
    from fastapi.testclient import TestClient
    from tests.conftest import CSRF
    pid = user_client.post("/api/posts", json={"title": "Mine", "body": "My experience in Goa"}).json()["id"]
    with TestClient(app, headers=CSRF) as other:
        other.post("/api/auth/register", json={"email": "intruder@example.com", "name": "I", "password": "Intrude-123"})
        assert other.delete(f"/api/posts/{pid}").status_code == 403
    assert user_client.delete(f"/api/posts/{pid}").status_code == 200


# ---------------------------------------------------------------- admin
def test_admin_stats_and_alerts(admin_client):
    s = admin_client.get("/api/admin/stats").json()
    assert s["destinations"] >= 45 and s["attractions"] >= 150 and s["users"] >= 1
    a = admin_client.get("/api/admin/alerts", params={"at": "2026-11-14T13:00"}).json()
    assert a["items"] and all(x["level"] in ("High", "At Capacity") for x in a["items"])
    p = [x["p_exceed"] for x in a["items"]]
    assert p == sorted(p, reverse=True)


def test_admin_destination_and_attraction_crud(admin_client):
    d = {"slug": "test-hill", "name": "Test Hill", "state_code": "KL", "lat": 10.0, "lon": 77.0,
         "categories": ["nature"], "budget": "low", "daily_cost": 1500, "min_days": 1, "best_months": [1, 2],
         "climate": "mountain", "description": "Test destination"}
    assert admin_client.post("/api/admin/destinations", json=d).status_code == 201
    assert admin_client.put("/api/admin/destinations/test-hill", json={"featured": True}).json()["featured"] is True
    a = {"destination": "test-hill", "name": "Test Falls", "category": "waterfall", "lat": 10.01, "lon": 77.01,
         "capacity": 200, "open_hour": 8, "close_hour": 17, "fee": 10}
    r = admin_client.post("/api/admin/attractions", json=a)
    assert r.status_code == 201, r.text
    slug = r.json()["slug"]
    f = admin_client.get(f"/api/attractions/{slug}/forecast", params={"date": "2026-11-14"}).json()
    assert f["hourly"]  # new attraction gets forecasts without its own history
    assert admin_client.put(f"/api/admin/attractions/{slug}", json={"capacity": 250}).json()["capacity"] == 250
    assert admin_client.delete(f"/api/admin/attractions/{slug}").status_code == 200
    assert admin_client.delete("/api/admin/destinations/test-hill").status_code == 200
    assert admin_client.get("/api/destinations/test-hill").status_code == 404


def test_admin_manages_users_reviews_reports_listings_sources(admin_client, user_client):
    users = admin_client.get("/api/admin/users").json()["items"]
    target = next(u for u in users if u["email"] == user_client.email)
    assert admin_client.patch(f"/api/admin/users/{target['id']}", json={"is_active": False}).status_code == 200
    assert user_client.get("/api/me/profile").status_code == 401  # deactivated users are signed out
    admin_client.patch(f"/api/admin/users/{target['id']}", json={"is_active": True})

    rv = admin_client.get("/api/admin/reviews").json()["items"][0]
    assert admin_client.patch(f"/api/admin/reviews/{rv['id']}", json={"status": "hidden"}).json()["status"] == "hidden"
    admin_client.patch(f"/api/admin/reviews/{rv['id']}", json={"status": "visible"})

    assert "items" in admin_client.get("/api/admin/content-reports").json()

    lst = {"destination": "goa", "name": "Test Homestay", "kind": "homestay", "description": "Demo"}
    lid = admin_client.post("/api/admin/listings", json=lst).json()["id"]
    assert admin_client.put(f"/api/admin/listings/{lid}", json={"verified": True}).json()["verified"] is True
    assert admin_client.delete(f"/api/admin/listings/{lid}").status_code == 200

    srcs = admin_client.get("/api/admin/data-sources").json()["items"]
    assert {s["key"] for s in srcs} >= {"catalogue", "crowd-demo", "open-meteo"}
    m = admin_client.get("/api/admin/system").json()
    assert m["model"]["test_metrics"] and m["database"] == "ok"


def test_admin_acts_on_content_report(admin_client, user_client):
    pid = user_client.post("/api/posts", json={"title": "Bad", "body": "Spam spam spam"}).json()["id"]
    rid = user_client.post("/api/content-reports", json={"target_type": "post", "target_id": pid, "reason": "Spam"}).json()["id"]
    r = admin_client.patch(f"/api/admin/content-reports/{rid}", json={"status": "actioned", "hide_target": True})
    assert r.status_code == 200
    assert user_client.get(f"/api/posts/{pid}").status_code == 404  # hidden from the public


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_unexpected_errors_do_not_leak_internals(client):
    r = client.get("/api/destinations/%00")
    assert r.status_code in (404, 422)
    assert "Traceback" not in r.text
