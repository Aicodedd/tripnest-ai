"""Test setup: an isolated SQLite database and model directory per test session.

Environment variables must be set before `app` is imported, because settings are read at import time.
"""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="tripnest-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["MODEL_DIR"] = f"{_TMP}/models"
os.environ["ENV"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-1234567890"
os.environ["WEATHER_PROVIDER"] = "off"  # never call the network from tests
os.environ["PHOTO_PROVIDER"] = "off"
os.environ["TRAIN_DAYS"] = "120"  # small, fast model for tests
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = "Admin-Pass-123"

import pytest  # noqa: E402

# Browsers send this header from TripNest pages; cross-site forms cannot (CSRF defence).
CSRF = {"X-Requested-With": "TripNest"}


@pytest.fixture(scope="session")
def app():
    from app.main import create_app
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient
    with TestClient(app, headers=CSRF) as c:
        yield c


@pytest.fixture()
def fresh_client(app):
    """A client with its own cookie jar (a different browser)."""
    from fastapi.testclient import TestClient
    with TestClient(app, headers=CSRF) as c:
        yield c


_counter = {"n": 0}


@pytest.fixture()
def user_client(app):
    """A logged-in traveller with a unique email."""
    from fastapi.testclient import TestClient
    _counter["n"] += 1
    email = f"traveller{_counter['n']}@example.com"
    with TestClient(app, headers=CSRF) as c:
        r = c.post("/api/auth/register", json={"email": email, "name": "Test Traveller", "password": "Str0ng-pass!"})
        assert r.status_code == 201, r.text
        c.email = email
        yield c


@pytest.fixture()
def admin_client(app):
    from fastapi.testclient import TestClient
    with TestClient(app, headers=CSRF) as c:
        r = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "Admin-Pass-123"})
        assert r.status_code == 200, r.text
        yield c
