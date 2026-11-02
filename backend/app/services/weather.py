"""Live weather from Open-Meteo (no API key). Failures produce an explicit 'unavailable' result, never invented data."""
from __future__ import annotations

import datetime as dt
import logging
import threading
import time

import httpx

from ..config import settings

log = logging.getLogger("tripnest.weather")
URL = "https://api.open-meteo.com/v1/forecast"
TTL = 1800
_cache: dict[tuple, tuple[float, dict]] = {}
_lock = threading.Lock()

WMO = {0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Rime fog",
       51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
       66: "Freezing rain", 67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
       80: "Rain showers", 81: "Rain showers", 82: "Violent rain showers", 85: "Snow showers", 86: "Snow showers",
       95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail"}


def _unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason, "source": "Open-Meteo"}


def suggestions(daily: list[dict]) -> list[str]:
    tips = []
    if not daily:
        return tips
    wet = [d for d in daily if (d.get("rain_chance") or 0) >= 60]
    hot = [d for d in daily if (d.get("max_c") or 0) >= 36]
    cold = [d for d in daily if (d.get("min_c") if d.get("min_c") is not None else 99) <= 5]
    if wet:
        tips.append(f"Rain likely on {len(wet)} of the next {len(daily)} days: plan covered places (museums, temples, "
                    "markets) for those afternoons and carry rain gear.")
    if hot:
        tips.append("Very hot days ahead: visit outdoor sites before 11 AM or after 4 PM and carry water.")
    if cold:
        tips.append("Near-freezing nights forecast: pack warm layers.")
    if not tips:
        tips.append("Settled weather forecast: a good window for outdoor sightseeing.")
    return tips


def forecast(lat: float, lon: float) -> dict:
    if settings.weather_provider != "open-meteo":
        return _unavailable("Live weather is turned off for this deployment (WEATHER_PROVIDER).")
    key = (round(lat, 2), round(lon, 2))
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < TTL:
            return hit[1]
    params = {"latitude": lat, "longitude": lon, "timezone": settings.timezone, "forecast_days": 7,
              "current": "temperature_2m,weather_code,precipitation,wind_speed_10m",
              "hourly": "precipitation_probability",
              "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"}
    try:
        r = httpx.get(URL, params=params, timeout=5.0)
        r.raise_for_status()
        j = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("weather fetch failed: %s", type(exc).__name__)
        return _unavailable("The weather service could not be reached. Try again later.")
    try:
        cur = j["current"]
        d = j["daily"]
        daily = [{"date": d["time"][i], "condition": WMO.get(d["weather_code"][i], "Unknown"),
                  "max_c": d["temperature_2m_max"][i], "min_c": d["temperature_2m_min"][i],
                  "rain_chance": d["precipitation_probability_max"][i]} for i in range(len(d["time"]))]
        hourly = {t: p for t, p in zip(j["hourly"]["time"], j["hourly"]["precipitation_probability"]) if p is not None}
        out = {"available": True, "source": "Open-Meteo (open-meteo.com)",
               "fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
               "current": {"temp_c": cur["temperature_2m"], "condition": WMO.get(cur["weather_code"], "Unknown"),
                           "precip_mm": cur.get("precipitation"), "wind_kmh": cur.get("wind_speed_10m"),
                           "observed_at": cur["time"]},
               "daily": daily, "hourly_rain": hourly, "suggestions": suggestions(daily)}
    except (KeyError, IndexError, TypeError):
        return _unavailable("The weather service returned an unexpected response.")
    with _lock:
        _cache[key] = (time.time(), out)
    return out


def rain_by_hour(lat: float, lon: float) -> dict:
    """{(date, hour): probability 0..1} from the live forecast, or {} when unavailable."""
    w = forecast(lat, lon)
    if not w.get("available"):
        return {}
    out = {}
    for t, p in w["hourly_rain"].items():
        ts = dt.datetime.fromisoformat(t)
        out[(ts.date(), ts.hour)] = p / 100
    return out
