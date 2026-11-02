"""Password hashing (bcrypt), session tokens (JWT) and login rate limiting."""
from __future__ import annotations

import datetime as dt
import threading
import time
from collections import defaultdict, deque

import bcrypt
import jwt

from .config import settings

COOKIE_NAME = "tn_session"
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    # bcrypt only uses the first 72 bytes; the schema caps passwords at 72 characters.
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_token(user_id: int, role: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {"sub": str(user_id), "role": role, "iat": now,
               "exp": now + dt.timedelta(minutes=settings.token_minutes)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


class LoginLimiter:
    """At most `limit` failed logins per (email, client IP) in `window` seconds."""

    def __init__(self, limit: int = 5, window: int = 300):
        self.limit, self.window = limit, window
        self._fails: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _key(self, email: str, ip: str) -> str:
        return f"{email.lower()}|{ip}"

    def blocked(self, email: str, ip: str) -> bool:
        with self._lock:
            q = self._fails[self._key(email, ip)]
            cutoff = time.monotonic() - self.window
            while q and q[0] < cutoff:
                q.popleft()
            return len(q) >= self.limit

    def fail(self, email: str, ip: str) -> None:
        with self._lock:
            self._fails[self._key(email, ip)].append(time.monotonic())

    def reset(self, email: str, ip: str) -> None:
        with self._lock:
            self._fails.pop(self._key(email, ip), None)


login_limiter = LoginLimiter()
