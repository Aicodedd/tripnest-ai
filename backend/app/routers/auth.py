"""Authentication, profile and favourites (EPIC-002)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import current_user, optional_user
from ..models import Destination, Favourite, User
from ..schemas import LoginIn, ProfileIn, RegisterIn
from ..security import COOKIE_NAME, create_token, hash_password, login_limiter, verify_password

router = APIRouter(prefix="/api", tags=["auth & profile"])


def user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role, "home_city": u.home_city,
            "home_lat": u.home_lat, "home_lon": u.home_lon, "interests": u.interests or [], "budget": u.budget,
            "group_type": u.group_type, "created_at": u.created_at.isoformat()}


def _set_session(resp: Response, user: User) -> None:
    resp.set_cookie(COOKIE_NAME, create_token(user.id, user.role), max_age=settings.token_minutes * 60,
                    httponly=True, samesite="lax", secure=settings.is_production, path="/")


@router.post("/auth/register", status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    u = User(email=email, name=body.name, password_hash=hash_password(body.password))
    db.add(u)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists")
    _set_session(response, u)
    return {"user": user_out(u)}


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    ip = request.client.host if request.client else "unknown"
    if login_limiter.blocked(email, ip):
        raise HTTPException(429, "Too many failed attempts. Please wait a few minutes and try again.")
    u = db.scalar(select(User).where(User.email == email))
    if not u or not u.is_active or not verify_password(body.password, u.password_hash):
        login_limiter.fail(email, ip)
        raise HTTPException(401, "Invalid email or password")
    login_limiter.reset(email, ip)
    _set_session(response, u)
    return {"user": user_out(u)}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/auth/session")
def session(user: User | None = Depends(optional_user)):
    """Who is signed in, without an error status when nobody is (used when the app starts)."""
    return {"user": user_out(user) if user else None}


@router.get("/auth/me")
def me(user: User = Depends(current_user)):
    return {"user": user_out(user)}


@router.get("/me/profile")
def get_profile(user: User = Depends(current_user)):
    return user_out(user)


@router.put("/me/profile")
def update_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.add(user)
    db.commit()
    return user_out(user)


def _dest(db: Session, slug: str) -> Destination:
    d = db.scalar(select(Destination).where(Destination.slug == slug))
    if not d:
        raise HTTPException(404, "Destination not found")
    return d


@router.get("/me/favourites")
def favourites(user: User = Depends(current_user), db: Session = Depends(get_db)):
    favs = db.scalars(select(Favourite).where(Favourite.user_id == user.id).order_by(Favourite.created_at)).all()
    return {"items": [{"slug": f.destination.slug, "name": f.destination.name, "state": f.destination.state.name,
                       "categories": f.destination.categories} for f in favs]}


@router.post("/me/favourites/{slug}", status_code=201)
def add_favourite(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _dest(db, slug)
    if not db.scalar(select(Favourite).where(Favourite.user_id == user.id, Favourite.destination_id == d.id)):
        db.add(Favourite(user_id=user.id, destination_id=d.id))
        db.commit()
    return {"ok": True}


@router.delete("/me/favourites/{slug}")
def remove_favourite(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _dest(db, slug)
    f = db.scalar(select(Favourite).where(Favourite.user_id == user.id, Favourite.destination_id == d.id))
    if f:
        db.delete(f)
        db.commit()
    return {"ok": True}
