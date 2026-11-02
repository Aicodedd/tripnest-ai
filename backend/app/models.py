"""Database models. Every table that holds external or demonstration content carries a `source` column
so the UI can always say where a value came from."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="traveller")  # traveller | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    home_city: Mapped[str | None] = mapped_column(String(80))
    home_lat: Mapped[float | None] = mapped_column(Float)
    home_lon: Mapped[float | None] = mapped_column(Float)
    interests: Mapped[list] = mapped_column(JSON, default=list)
    budget: Mapped[str | None] = mapped_column(String(10))  # low | mid | high
    group_type: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

    favourites: Mapped[list[Favourite]] = relationship(back_populates="user", cascade="all, delete-orphan")


class State(Base):
    __tablename__ = "states"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(4), unique=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    kind: Mapped[str] = mapped_column(String(10))  # state | ut
    region: Mapped[str] = mapped_column(String(20))
    destinations: Mapped[list[Destination]] = relationship(back_populates="state")


class Destination(Base):
    __tablename__ = "destinations"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    categories: Mapped[list] = mapped_column(JSON, default=list)
    budget: Mapped[str] = mapped_column(String(10), default="mid")  # low | mid | high
    daily_cost: Mapped[int] = mapped_column(Integer, default=2500)  # indicative INR per person per day
    min_days: Mapped[int] = mapped_column(Integer, default=2)
    best_months: Mapped[list] = mapped_column(JSON, default=list)  # 1..12
    climate: Mapped[str] = mapped_column(String(20), default="tropical")
    description: Mapped[str] = mapped_column(Text, default="")
    how_to_reach: Mapped[str] = mapped_column(Text, default="")
    facilities: Mapped[list] = mapped_column(JSON, default=list)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    popularity: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(40), default="catalogue")
    # Photograph (Wikimedia Commons): URL and credit are stored so every card shows the same image with its licence
    image_url: Mapped[str | None] = mapped_column(String(500))
    image_title: Mapped[str | None] = mapped_column(String(200))
    image_credit: Mapped[str | None] = mapped_column(String(300))
    image_licence: Mapped[str | None] = mapped_column(String(80))
    image_source_page: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    state: Mapped[State] = relationship(back_populates="destinations")
    attractions: Mapped[list[Attraction]] = relationship(back_populates="destination", cascade="all, delete-orphan")
    listings: Mapped[list[Listing]] = relationship(back_populates="destination", cascade="all, delete-orphan")


class Attraction(Base):
    __tablename__ = "attractions"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(140))
    category: Mapped[str] = mapped_column(String(30))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer)  # ASSUMED carrying capacity (people at once)
    popularity: Mapped[float] = mapped_column(Float, default=0.8)
    open_hour: Mapped[int] = mapped_column(Integer, default=9)
    close_hour: Mapped[int] = mapped_column(Integer, default=18)
    fee: Mapped[int] = mapped_column(Integer, default=0)  # indicative INR
    sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    family_friendly: Mapped[bool] = mapped_column(Boolean, default=True)
    elder_friendly: Mapped[bool] = mapped_column(Boolean, default=True)
    covered: Mapped[bool] = mapped_column(Boolean, default=False)
    visit_min: Mapped[int] = mapped_column(Integer, default=60)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(40), default="catalogue")

    destination: Mapped[Destination] = relationship(back_populates="attractions")


class Favourite(Base):
    __tablename__ = "favourites"
    __table_args__ = (UniqueConstraint("user_id", "destination_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    user: Mapped[User] = relationship(back_populates="favourites")
    destination: Mapped[Destination] = relationship()


class Itinerary(Base):
    __tablename__ = "itineraries"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[dt.date] = mapped_column(Date)
    days: Mapped[int] = mapped_column(Integer)
    params: Mapped[dict] = mapped_column(JSON, default=dict)  # destinations, interests, budget, group, pace
    plan: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), index=True)
    attraction_id: Mapped[int | None] = mapped_column(ForeignKey("attractions.id", ondelete="SET NULL"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    sentiment: Mapped[str] = mapped_column(String(10))
    score: Mapped[float] = mapped_column(Float)
    aspects: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(10), default="user")  # user | demo
    status: Mapped[str] = mapped_column(String(10), default="visible")  # visible | hidden
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    destination: Mapped[Destination] = relationship()
    user: Mapped[User | None] = relationship()
    attraction: Mapped[Attraction | None] = relationship()


class CrowdReport(Base):
    __tablename__ = "crowd_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    attraction_id: Mapped[int] = mapped_column(ForeignKey("attractions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    level: Mapped[str] = mapped_column(String(10))  # low | moderate | high | packed
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Listing(Base):
    """Local businesses / stays / services shown on a destination page."""
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(primary_key=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))  # homestay | food | guide | shop | transport
    description: Mapped[str] = mapped_column(Text, default="")
    price_band: Mapped[str | None] = mapped_column(String(10))
    contact: Mapped[str | None] = mapped_column(String(120))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(40), default="demo")
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    destination: Mapped[Destination] = relationship(back_populates="listings")


class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    destination_id: Mapped[int | None] = mapped_column(ForeignKey("destinations.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(140))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="visible")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, index=True)
    user: Mapped[User] = relationship()
    destination: Mapped[Destination | None] = relationship()
    comments: Mapped[list[Comment]] = relationship(back_populates="post", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="visible")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    post: Mapped[Post] = relationship(back_populates="comments")
    user: Mapped[User] = relationship()


class ContentReport(Base):
    __tablename__ = "content_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    target_type: Mapped[str] = mapped_column(String(10))  # post | comment | review
    target_id: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(10), default="open")  # open | actioned | dismissed
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    reporter: Mapped[User] = relationship()


class DataSource(Base):
    """Registry of where data comes from, shown to admins and in provenance labels."""
    __tablename__ = "data_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))  # live | catalogue | demonstration | model
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text, default="")
    last_updated: Mapped[dt.datetime | None] = mapped_column(DateTime)
