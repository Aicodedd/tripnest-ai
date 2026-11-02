"""Place photographs from Wikipedia / Wikimedia Commons, with credit and licence.

The browser loads the image straight from upload.wikimedia.org; TripNest stores only the URL and its
credit. Only Wikimedia-hosted images are accepted. Failures return an explicit 'unavailable' result.
"""
from __future__ import annotations

import html
import logging
import os
import re
import threading
import time

import httpx

log = logging.getLogger("tripnest.photos")
WIKI = "https://en.wikipedia.org/w/api.php"
COMMONS = "https://commons.wikimedia.org/w/api.php"
# Wikimedia requires a contact URL or email in the User-Agent; without one, API calls get HTTP 403.
CONTACT = os.environ.get("WIKIMEDIA_CONTACT", "https://github.com/tripnest-ai/tripnest-ai")
HEADERS = {"User-Agent": f"TripNestAI/1.0 ({CONTACT}) crowd-aware travel planner"}
TTL = 24 * 3600
_cache: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()
ALLOWED = re.compile(r"^https://(upload|thumb)\.wikimedia\.org/")


def enabled() -> bool:
    return os.environ.get("PHOTO_PROVIDER", "wikimedia") == "wikimedia"


def _unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason}


def _text(v: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", v or ""))).strip()


def parse(page_json: dict, meta_json: dict | None) -> dict:
    """Turn the Wikipedia search result (+ optional Commons metadata) into a photo record."""
    pages = list(((page_json or {}).get("query") or {}).get("pages", {}).values())
    if not pages:
        return _unavailable("No matching article")
    pages.sort(key=lambda p: p.get("index", 0))
    p = next((x for x in pages if x.get("thumbnail", {}).get("source")), None)
    if not p:
        return _unavailable("No photograph found for this place")
    url = p["thumbnail"]["source"].split("?")[0]  # drop tracking parameters
    if not ALLOWED.match(url):
        return _unavailable("Image is not hosted on Wikimedia")
    out = {"available": True, "url": url, "width": p["thumbnail"].get("width"), "height": p["thumbnail"].get("height"),
           "title": p.get("title"), "article": p.get("fullurl"), "credit": "Wikimedia Commons contributor",
           "licence": "See source page", "source_page": None, "source": "Wikipedia / Wikimedia Commons"}
    info = list(((meta_json or {}).get("query") or {}).get("pages", {}).values())
    if info and info[0].get("imageinfo"):
        ii = info[0]["imageinfo"][0]
        em = ii.get("extmetadata", {})
        out["credit"] = _text(em.get("Artist", {}).get("value")) or out["credit"]
        out["licence"] = _text(em.get("LicenseShortName", {}).get("value")) or out["licence"]
        out["source_page"] = ii.get("descriptionurl")
    if not out["source_page"] and p.get("pageimage"):
        out["source_page"] = f"https://commons.wikimedia.org/wiki/File:{p['pageimage']}"
    return out


def lookup(query: str, size: int = 800) -> dict:
    if not enabled():
        return _unavailable("Place photos are turned off for this deployment (PHOTO_PROVIDER).")
    key = f"{query}|{size}"
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < TTL:
            return hit[1]
    try:
        r = httpx.get(WIKI, headers=HEADERS, timeout=6.0, params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": query, "gsrlimit": 3,
            "prop": "pageimages|info", "piprop": "thumbnail|name", "pithumbsize": size, "inprop": "url"})
        r.raise_for_status()
        page = r.json()
        meta = None
        pages = list((page.get("query") or {}).get("pages", {}).values())
        pages.sort(key=lambda p: p.get("index", 0))
        first = next((x for x in pages if x.get("pageimage") and x.get("thumbnail")), None)
        if first:
            m = httpx.get(COMMONS, headers=HEADERS, timeout=6.0, params={
                "action": "query", "format": "json", "titles": f"File:{first['pageimage']}", "prop": "imageinfo",
                "iiprop": "extmetadata|url"})
            if m.status_code == 200:
                meta = m.json()
        out = parse(page, meta)
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("photo lookup failed: %s", type(exc).__name__)
        return _unavailable("The photo service could not be reached.")
    with _lock:
        _cache[key] = (time.time(), out)
    return out
