"""Runtime configuration from environment variables (see .env.example).

Secrets are read here and nowhere else. In production a missing SECRET_KEY or DATABASE_URL
stops the app at startup with a clear message instead of running insecurely.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE lines). Real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv(ROOT_DIR / ".env")


class ConfigError(RuntimeError):
    pass


def _db_url(raw: str | None) -> str:
    if not raw:
        return f"sqlite:///{BACKEND_DIR / 'tripnest.db'}"
    # Render/Heroku style URLs -> SQLAlchemy psycopg3 driver
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]
    if raw.startswith("postgresql://"):
        raw = "postgresql+psycopg://" + raw[len("postgresql://"):]
    return raw


@dataclass
class Settings:
    env: str = field(default_factory=lambda: os.environ.get("ENV", "development"))
    database_url: str = field(default_factory=lambda: _db_url(os.environ.get("DATABASE_URL")))
    secret_key: str = field(default_factory=lambda: os.environ.get("SECRET_KEY", ""))
    token_minutes: int = field(default_factory=lambda: int(os.environ.get("TOKEN_MINUTES", "720")))
    allowed_origins: list[str] = field(default_factory=lambda: [
        o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()])
    timezone: str = field(default_factory=lambda: os.environ.get("APP_TZ", "Asia/Kolkata"))
    weather_provider: str = field(default_factory=lambda: os.environ.get("WEATHER_PROVIDER", "open-meteo"))
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    model_dir: Path = field(default_factory=lambda: Path(os.environ.get("MODEL_DIR", BACKEND_DIR / "models")))
    frontend_dir: Path = field(default_factory=lambda: ROOT_DIR / "frontend")

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    def validate(self) -> None:
        if self.is_production:
            missing = [n for n, v in (("SECRET_KEY", self.secret_key),
                                      ("DATABASE_URL", os.environ.get("DATABASE_URL"))) if not v]
            if missing:
                raise ConfigError(f"Missing required environment variable(s): {', '.join(missing)}. "
                                  "See .env.example and docs/DEPLOYMENT_GUIDE.md.")
            if len(self.secret_key) < 32:
                raise ConfigError("SECRET_KEY must be at least 32 characters in production.")
        elif not self.secret_key:
            # development only: a random per-process key (sessions reset on restart)
            self.secret_key = secrets.token_urlsafe(48)


settings = Settings()
