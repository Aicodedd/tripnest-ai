"""EPIC-002 Accounts: registration, login, logout, profile, favourites, access control."""
from fastapi.testclient import TestClient

from tests.conftest import CSRF


def test_health_reports_database_and_model(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["database"] == "ok" and body["model"]["loaded"] is True


def test_register_login_logout_round_trip(app):
    with TestClient(app, headers=CSRF) as c:
        r = c.post("/api/auth/register", json={"email": "Asha@Example.com", "name": "Asha", "password": "Goa-trip-2026"})
        assert r.status_code == 201
        assert r.json()["user"]["email"] == "asha@example.com"  # normalised
        assert "password" not in r.text and "password_hash" not in r.text
        assert c.get("/api/auth/me").json()["user"]["name"] == "Asha"
        assert c.post("/api/auth/logout").status_code == 200
        assert c.get("/api/auth/me").status_code == 401
        r = c.post("/api/auth/login", json={"email": "asha@example.com", "password": "Goa-trip-2026"})
        assert r.status_code == 200 and c.get("/api/auth/me").status_code == 200


def test_session_cookie_is_httponly(app):
    with TestClient(app, headers=CSRF) as c:
        r = c.post("/api/auth/register", json={"email": "cookie@example.com", "name": "C", "password": "Cookie-123x"})
        cookie = r.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=lax" in cookie


def test_password_is_stored_hashed(client):
    client.post("/api/auth/register", json={"email": "hash@example.com", "name": "H", "password": "Hashed-pass-9"})
    from app.db import SessionLocal
    from app.models import User
    with SessionLocal() as db:
        u = db.query(User).filter_by(email="hash@example.com").one()
        assert u.password_hash.startswith("$2") and "Hashed-pass-9" not in u.password_hash


def test_duplicate_email_is_rejected(client):
    body = {"email": "dup@example.com", "name": "D", "password": "Dup-pass-123"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    assert client.post("/api/auth/register", json=body).status_code == 409


def test_weak_password_and_bad_email_are_rejected(client):
    assert client.post("/api/auth/register", json={"email": "w@example.com", "name": "W", "password": "short"}).status_code == 422
    assert client.post("/api/auth/register", json={"email": "not-an-email", "name": "W", "password": "Long-enough-1"}).status_code == 422


def test_wrong_password_gives_generic_error(client):
    r = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "Whatever-123"})
    assert r.status_code == 401 and r.json()["detail"] == "Invalid email or password"


def test_repeated_failed_logins_are_rate_limited(fresh_client):
    fresh_client.headers.update(CSRF)
    codes = [fresh_client.post("/api/auth/login", json={"email": "victim@example.com", "password": f"Guess-{i}xx"}).status_code
             for i in range(7)]
    assert codes[:5] == [401] * 5 and 429 in codes[5:]


def test_state_changing_request_without_csrf_header_is_refused(app):
    with TestClient(app) as c:  # no X-Requested-With header
        c.headers.update(CSRF)
        c.post("/api/auth/register", json={"email": "csrf@example.com", "name": "C", "password": "Csrf-pass-123"})
        del c.headers["X-Requested-With"]
        r = c.put("/api/me/profile", json={"name": "Hacked"})
        assert r.status_code == 403


def test_profile_update_and_preferences(user_client):
    r = user_client.put("/api/me/profile", json={"name": "Priya", "home_city": "Chennai", "home_lat": 13.08,
                                                 "home_lon": 80.27, "interests": ["beach", "heritage"],
                                                 "budget": "mid", "group_type": "family"})
    assert r.status_code == 200, r.text
    me = user_client.get("/api/me/profile").json()
    assert me["name"] == "Priya" and me["interests"] == ["beach", "heritage"] and me["group_type"] == "family"


def test_profile_rejects_unknown_budget(user_client):
    assert user_client.put("/api/me/profile", json={"budget": "luxury-plus"}).status_code == 422


def test_favourites_add_list_remove(user_client):
    assert user_client.post("/api/me/favourites/jaipur").status_code == 201
    assert user_client.post("/api/me/favourites/jaipur").status_code == 201  # idempotent
    favs = user_client.get("/api/me/favourites").json()["items"]
    assert [f["slug"] for f in favs] == ["jaipur"]
    assert user_client.delete("/api/me/favourites/jaipur").status_code == 200
    assert user_client.get("/api/me/favourites").json()["items"] == []


def test_private_endpoints_require_login(fresh_client):
    assert fresh_client.get("/api/me/profile").status_code == 401
    assert fresh_client.get("/api/itineraries").status_code == 401


def test_traveller_cannot_use_admin_endpoints(user_client):
    assert user_client.get("/api/admin/stats").status_code == 403


def test_session_endpoint_returns_null_user_when_signed_out(fresh_client):
    r = fresh_client.get("/api/auth/session")
    assert r.status_code == 200 and r.json() == {"user": None}


def test_session_endpoint_returns_user_when_signed_in(user_client):
    r = user_client.get("/api/auth/session")
    assert r.status_code == 200 and r.json()["user"]["email"] == user_client.email
