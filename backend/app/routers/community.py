"""Travel community: posts, comments and content reports (EPIC-008).

User text is stored as plain text and always rendered with textContent / escaping in the browser.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import Comment, ContentReport, Destination, Post, Review, User
from ..schemas import CommentIn, ContentReportIn, PostIn

router = APIRouter(prefix="/api", tags=["community"])
GUIDELINES = [
    "Share honest, first-hand travel experiences.",
    "Be respectful: no hate speech, harassment or personal attacks.",
    "No spam, advertising or misleading information.",
    "Do not post personal data such as phone numbers or addresses of other people.",
    "Respect local cultures and protected sites; do not encourage unsafe or illegal activity.",
]


def post_out(p: Post, with_comments: bool = False) -> dict:
    out = {"id": p.id, "title": p.title, "body": p.body, "author": p.user.name,
           "destination": {"slug": p.destination.slug, "name": p.destination.name} if p.destination else None,
           "created_at": p.created_at.isoformat(),
           "comment_count": sum(c.status == "visible" for c in p.comments)}
    if with_comments:
        out["comments"] = [{"id": c.id, "body": c.body, "author": c.user.name, "created_at": c.created_at.isoformat()}
                           for c in p.comments if c.status == "visible"]
    return out


@router.get("/community/guidelines")
def guidelines():
    return {"items": GUIDELINES}


@router.get("/posts")
def posts(destination: str | None = Query(None, max_length=80), page: int = Query(1, ge=1, le=100),
          db: Session = Depends(get_db)):
    stmt = select(Post).where(Post.status == "visible")
    if destination:
        stmt = stmt.join(Destination).where(Destination.slug == destination)
    rows = db.scalars(stmt.order_by(Post.created_at.desc(), Post.id.desc()).offset((page - 1) * 20).limit(20)).all()
    return {"items": [post_out(p) for p in rows], "page": page}


@router.post("/posts", status_code=201)
def create_post(body: PostIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    dest_id = None
    if body.destination:
        d = db.scalar(select(Destination).where(Destination.slug == body.destination))
        if not d:
            raise HTTPException(404, "Destination not found")
        dest_id = d.id
    p = Post(user_id=user.id, destination_id=dest_id, title=body.title.strip(), body=body.body.strip())
    db.add(p)
    db.commit()
    db.refresh(p)
    return post_out(p)


def _visible_post(db: Session, pid: int) -> Post:
    p = db.get(Post, pid)
    if not p or p.status != "visible":
        raise HTTPException(404, "Post not found")
    return p


@router.get("/posts/{pid}")
def get_post(pid: int, db: Session = Depends(get_db)):
    return post_out(_visible_post(db, pid), with_comments=True)


@router.post("/posts/{pid}/comments", status_code=201)
def comment(pid: int, body: CommentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _visible_post(db, pid)
    c = Comment(post_id=p.id, user_id=user.id, body=body.body.strip())
    db.add(c)
    db.commit()
    return {"id": c.id, "body": c.body, "author": user.name, "created_at": c.created_at.isoformat()}


@router.delete("/posts/{pid}")
def delete_post(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _visible_post(db, pid)
    if p.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "You can only delete your own posts")
    db.delete(p)
    db.commit()
    return {"ok": True}


TARGETS = {"post": Post, "comment": Comment, "review": Review}


@router.post("/content-reports", status_code=201)
def report(body: ContentReportIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    target = db.get(TARGETS[body.target_type], body.target_id)
    if not target:
        raise HTTPException(404, "The reported content does not exist")
    r = ContentReport(reporter_id=user.id, target_type=body.target_type, target_id=body.target_id,
                      reason=body.reason.strip())
    db.add(r)
    db.commit()
    return {"id": r.id, "status": r.status}
