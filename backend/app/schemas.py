"""Request validation schemas. Every free-text field has a length limit."""
from __future__ import annotations

import datetime as dt
import re
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

Budget = Literal["low", "mid", "high"]
Group = Literal["solo", "couple", "family", "elders", "friends"]
Pace = Literal["relaxed", "normal", "packed"]
CrowdLevel = Literal["low", "moderate", "high", "packed"]
Interest = str  # free tag, validated by length


def _tags(v: list[str]) -> list[str]:
    out = []
    for t in v:
        t = t.strip().lower()
        if not re.fullmatch(r"[a-z][a-z \-]{0,29}", t):
            raise ValueError(f"invalid interest '{t}'")
        if t not in out:
            out.append(t)
    return out[:12]


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def strong(cls, v: str) -> str:
        if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
            raise ValueError("password must contain letters and numbers")
        return v

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name is required")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class ProfileIn(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=80)
    home_city: str | None = Field(None, max_length=80)
    home_lat: float | None = Field(None, ge=-90, le=90)
    home_lon: float | None = Field(None, ge=-180, le=180)
    interests: list[Interest] | None = Field(None, max_length=12)
    budget: Budget | None = None
    group_type: Group | None = None

    @field_validator("interests")
    @classmethod
    def clean_interests(cls, v):
        return _tags(v) if v is not None else v


class Origin(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class RecommendIn(BaseModel):
    interests: list[Interest] = Field(default_factory=list, max_length=12)
    budget: Budget = "mid"
    days: int = Field(3, ge=1, le=30)
    group_type: Group = "couple"
    travel_date: dt.date | None = None
    origin: Origin | None = None
    max_distance_km: int | None = Field(None, ge=10, le=5000)
    limit: int = Field(8, ge=1, le=10)

    @field_validator("interests")
    @classmethod
    def clean_interests(cls, v):
        return _tags(v)


def _check_date(v: dt.date) -> dt.date:
    today = dt.date.today()
    if not (today - dt.timedelta(days=365) <= v <= today + dt.timedelta(days=548)):
        raise ValueError("date must be within the next 18 months")
    return v


class PlanIn(BaseModel):
    destinations: list[str] = Field(min_length=1, max_length=3)
    start_date: dt.date
    days: int = Field(ge=1, le=10)
    interests: list[Interest] = Field(default_factory=list, max_length=12)
    group_type: Group = "couple"
    budget: Budget = "mid"
    pace: Pace = "normal"

    @field_validator("interests")
    @classmethod
    def clean_interests(cls, v):
        return _tags(v)

    @field_validator("start_date")
    @classmethod
    def near_date(cls, v):
        return _check_date(v)


class ItinerarySaveIn(PlanIn):
    title: str = Field(min_length=1, max_length=120)


class DayEdit(BaseModel):
    stops: list[str] = Field(max_length=8)


class ItineraryEditIn(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=120)
    notes: str | None = Field(None, max_length=2000)
    days: list[DayEdit] | None = Field(None, max_length=10)


class RegenerateIn(BaseModel):
    interests: list[Interest] | None = None
    group_type: Group | None = None
    pace: Pace | None = None
    budget: Budget | None = None


class CrowdReportIn(BaseModel):
    level: CrowdLevel
    note: str | None = Field(None, max_length=300)
    at: dt.datetime | None = None  # demo clock; must be near the present


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=10, max_length=1500)
    attraction: str | None = Field(None, max_length=100)


class PostIn(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    body: str = Field(min_length=3, max_length=5000)
    destination: str | None = Field(None, max_length=80)


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=1500)


class ContentReportIn(BaseModel):
    target_type: Literal["post", "comment", "review"]
    target_id: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=300)


# ------------------------------------------------------------------ admin
Category = Literal["adventure", "beach", "garden", "heritage", "lake", "market", "museum", "nature", "plantation",
                   "river", "spiritual", "viewpoint", "waterfall", "wildlife"]
Climate = Literal["coastal", "desert", "mountain", "plains", "tropical"]
SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class DestinationIn(BaseModel):
    slug: str = Field(pattern=SLUG, max_length=80)
    name: str = Field(min_length=2, max_length=120)
    state_code: str = Field(min_length=2, max_length=4)
    lat: float = Field(ge=6, le=37.5)   # India's bounding box
    lon: float = Field(ge=68, le=98)
    categories: list[str] = Field(default_factory=list, max_length=10)
    budget: Budget = "mid"
    daily_cost: int = Field(2500, ge=0, le=100000)
    min_days: int = Field(1, ge=1, le=30)
    best_months: list[int] = Field(default_factory=list, max_length=12)
    climate: Climate = "plains"
    description: str = Field("", max_length=2000)
    how_to_reach: str = Field("", max_length=1000)
    featured: bool = False
    popularity: float = Field(1.0, ge=0.05, le=2.0)


class DestinationPatch(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    categories: list[str] | None = Field(None, max_length=10)
    budget: Budget | None = None
    daily_cost: int | None = Field(None, ge=0, le=100000)
    min_days: int | None = Field(None, ge=1, le=30)
    best_months: list[int] | None = None
    description: str | None = Field(None, max_length=2000)
    how_to_reach: str | None = Field(None, max_length=1000)
    featured: bool | None = None
    popularity: float | None = Field(None, ge=0.05, le=2.0)


class AttractionIn(BaseModel):
    destination: str = Field(max_length=80)
    name: str = Field(min_length=2, max_length=140)
    category: Category
    lat: float = Field(ge=6, le=37.5)
    lon: float = Field(ge=68, le=98)
    capacity: int = Field(ge=10, le=100000)
    popularity: float = Field(0.8, ge=0.05, le=2.0)
    open_hour: int = Field(9, ge=0, le=23)
    close_hour: int = Field(18, ge=1, le=24)
    fee: int = Field(0, ge=0, le=100000)
    sensitive: bool = False
    family_friendly: bool = True
    elder_friendly: bool = True
    covered: bool = False
    visit_min: int = Field(60, ge=10, le=600)
    tags: list[str] = Field(default_factory=list, max_length=10)
    description: str = Field("", max_length=2000)


class AttractionPatch(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=140)
    capacity: int | None = Field(None, ge=10, le=100000)
    popularity: float | None = Field(None, ge=0.05, le=2.0)
    open_hour: int | None = Field(None, ge=0, le=23)
    close_hour: int | None = Field(None, ge=1, le=24)
    fee: int | None = Field(None, ge=0, le=100000)
    sensitive: bool | None = None
    family_friendly: bool | None = None
    elder_friendly: bool | None = None
    covered: bool | None = None
    visit_min: int | None = Field(None, ge=10, le=600)
    tags: list[str] | None = Field(None, max_length=10)
    description: str | None = Field(None, max_length=2000)


class UserPatch(BaseModel):
    role: Literal["traveller", "admin"] | None = None
    is_active: bool | None = None


class StatusPatch(BaseModel):
    status: Literal["visible", "hidden"]


class ReportPatch(BaseModel):
    status: Literal["open", "actioned", "dismissed"]
    hide_target: bool = False


class ListingIn(BaseModel):
    destination: str = Field(max_length=80)
    name: str = Field(min_length=2, max_length=120)
    kind: Literal["homestay", "food", "guide", "shop", "transport"]
    description: str = Field("", max_length=1000)
    price_band: Literal["low", "mid", "high"] | None = None
    contact: str | None = Field(None, max_length=120)
    verified: bool = False


class ListingPatch(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    description: str | None = Field(None, max_length=1000)
    price_band: Literal["low", "mid", "high"] | None = None
    contact: str | None = Field(None, max_length=120)
    verified: bool | None = None


class DataSourcePatch(BaseModel):
    enabled: bool
