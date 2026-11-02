"""Shared runtime state: the loaded crowd model, attraction specs and a small forecast cache."""
from __future__ import annotations

import datetime as dt
import logging
import os
import threading
from collections import OrderedDict

from ..config import settings
from ..models import Attraction
from . import crowd, crowd_sim
from .forecast import CrowdModel

log = logging.getLogger("tripnest.model")
_lock = threading.Lock()
_state: dict = {"model": None}
_cache: OrderedDict = OrderedDict()
CACHE_SIZE = 4000


def spec(a: Attraction) -> dict:
    d = a.destination
    return dict(key=a.slug, category=a.category, capacity=a.capacity, popularity=a.popularity,
                open_hour=a.open_hour, close_hour=a.close_hour, covered=a.covered, sensitive=a.sensitive,
                best_months=list(d.best_months or []), climate=d.climate)


def model() -> CrowdModel:
    m = _state["model"]
    if m is None:
        raise RuntimeError("Crowd model is not loaded")
    return m


def load_or_train(specs: list[dict]) -> CrowdModel:
    with _lock:
        path = settings.model_dir / "crowd_model.joblib"
        if path.exists():
            try:
                m = CrowdModel.load(settings.model_dir)
                log.info("crowd model loaded (trained %s)", m.info.get("trained_at"))
                _state["model"] = m
                return m
            except Exception as exc:  # corrupted or incompatible artefact -> retrain
                log.warning("model artefact unreadable (%s); retraining", type(exc).__name__)
        days = int(os.environ.get("TRAIN_DAYS", "365"))
        log.info("training crowd model on %d attractions x %d days of demonstration data", len(specs), days)
        m = CrowdModel()
        info = m.train(specs, end_date=dt.date.today(), days=days)
        m.save(settings.model_dir)
        log.info("model trained in %ss, test MAPE %s%%", info["seconds"], info["test_metrics"]["mape"])
        _state["model"] = m
        _cache.clear()
        return m


def _cache_key(s: dict, d: dt.date) -> tuple:
    return (s["key"], s["category"], s["capacity"], s["popularity"], s["open_hour"], s["close_hour"], s["covered"],
            s["sensitive"], tuple(s["best_months"]), s["climate"], d)


def day_forecast(s: dict, d: dt.date) -> list[dict]:
    k = _cache_key(s, d)
    if k in _cache:
        _cache.move_to_end(k)
        return _cache[k]
    out = crowd.day_forecast(model(), s, d)
    _cache[k] = out
    if len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)
    return out


def prefetch_day(specs: list[dict], d: dt.date) -> None:
    """Forecast every uncached attraction for day d in ONE model call (instead of one call each)."""
    todo = [s for s in specs if _cache_key(s, d) not in _cache]
    if not todo:
        return
    m = model()
    rows, spans = [], []
    for s in todo:
        r = crowd.day_rows(s, d)
        spans.append((s, len(rows), len(r)))
        rows += r
    utils = m.predict_util(rows) if rows else []
    for s, start, n in spans:
        hours = [r[2] for r in rows[start:start + n]]
        _cache[_cache_key(s, d)] = crowd.shape_day(m, s, hours, utils[start:start + n])
    while len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)


def util_at(s: dict, t: dt.datetime) -> float | None:
    """Predicted utilisation at a moment (linear between hours); None when closed."""
    if not (s["open_hour"] <= t.hour < s["close_hour"]):
        return None
    by_h = {h["hour"]: h["util"] for h in day_forecast(s, t.date())}
    u0 = by_h.get(t.hour)
    if u0 is None:  # outside modelled 5 AM-11 PM window
        return 0.0
    u1 = by_h.get(t.hour + 1, u0)
    f = t.minute / 60
    return u0 * (1 - f) + u1 * f


def provenance(adjusted_reports: int = 0) -> dict:
    m = model()
    return {
        "type": "model-predicted",
        "training_data": m.info.get("data_provenance", "demonstration"),
        "model_trained_at": m.info.get("trained_at"),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "adjusted_by_reports": adjusted_reports,
        "note": "Forecast from a model trained on DEMONSTRATION crowd data (no verified visitor counts). "
                "Use as guidance, not fact." + (f" Adjusted by {adjusted_reports} recent traveller report(s)."
                                                 if adjusted_reports else ""),
    }


def is_open(s: dict, t: dt.datetime) -> bool:
    return s["open_hour"] <= t.hour < s["close_hour"]


def now_local() -> dt.datetime:
    from zoneinfo import ZoneInfo
    return dt.datetime.now(ZoneInfo(settings.timezone)).replace(tzinfo=None, second=0, microsecond=0)


__all__ = ["spec", "model", "load_or_train", "day_forecast", "util_at", "provenance", "crowd_sim"]
