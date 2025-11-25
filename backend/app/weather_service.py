"""
Weather service: fetch current/near-term conditions and assess mission risk.

This module uses Open-Meteo (no API key required) and gracefully degrades when
data is unavailable. It returns a simple risk assessment aligned with the spec:
  - safe: conditions nominales
  - caution: conditions dégradées (vol possible avec marges)
  - blocked: conditions dangereuses (vol à différer)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import json
import ssl
from urllib import request, parse


@dataclass
class WeatherMetrics:
    wind_speed: Optional[float] = None  # m/s
    wind_gusts: Optional[float] = None  # m/s
    precipitation: Optional[float] = None  # mm
    temperature: Optional[float] = None  # °C
    timestamp: datetime = datetime.now(timezone.utc)


@dataclass
class WeatherAssessment:
    risk: str  # 'safe' | 'caution' | 'blocked'
    reason: str
    metrics: WeatherMetrics


def _safe_get(obj: Dict[str, Any], *keys):
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def fetch_weather(lat: float, lon: float) -> WeatherMetrics:
    """
    Fetch current weather metrics from Open-Meteo.
    Returns metrics with None fields if fetch fails.
    """
    base = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": f"{lat}",
        "longitude": f"{lon}",
        # Request both 'current' and near-term 'hourly' to improve robustness
        "current": "temperature_2m,precipitation,wind_speed_10m,wind_gusts_10m",
        "hourly": "precipitation,wind_speed_10m,wind_gusts_10m",
        "timezone": "UTC",
    }
    url = f"{base}?{parse.urlencode(params)}"

    ctx = ssl.create_default_context()
    try:
        with request.urlopen(url, context=ctx, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        # Network or parsing error; return empty metrics
        return WeatherMetrics()

    # Try current metrics first
    cur = _safe_get(data, "current") or {}
    wind_speed = cur.get("wind_speed_10m") or cur.get("windspeed_10m")
    wind_gusts = cur.get("wind_gusts_10m") or cur.get("windgusts_10m")
    precipitation = cur.get("precipitation")
    temperature = cur.get("temperature_2m")

    # Fallback to first hourly slot when current not present
    hourly = _safe_get(data, "hourly") or {}
    def _first(lst):
        return lst[0] if isinstance(lst, list) and lst else None
    wind_speed = wind_speed if wind_speed is not None else _first(hourly.get("wind_speed_10m") or hourly.get("windspeed_10m"))
    wind_gusts = wind_gusts if wind_gusts is not None else _first(hourly.get("wind_gusts_10m") or hourly.get("windgusts_10m"))
    precipitation = precipitation if precipitation is not None else _first(hourly.get("precipitation"))

    return WeatherMetrics(
        wind_speed=_to_float(wind_speed),
        wind_gusts=_to_float(wind_gusts),
        precipitation=_to_float(precipitation),
        temperature=_to_float(temperature),
        timestamp=datetime.now(timezone.utc),
    )


def _to_float(val: Any) -> Optional[float]:
    try:
        if val is None:
            return None
        return float(val)
    except Exception:
        return None


def assess_weather(metrics: WeatherMetrics) -> WeatherAssessment:
    """
    Assess risk based on simple thresholds inspired by the spec.
    Thresholds (conservative):
      - wind_speed > 12 m/s or gusts > 18 m/s => blocked
      - precipitation > 5 mm/h => caution (<= 10 mm/h blocked)
      - otherwise safe
    """
    wind = metrics.wind_speed or 0.0
    gust = metrics.wind_gusts or 0.0
    rain = metrics.precipitation or 0.0

    if wind > 12.0 or gust > 18.0 or rain > 10.0:
        return WeatherAssessment(
            risk="blocked",
            reason="Conditions dangereuses (vent fort/grosses rafales ou pluie intense)",
            metrics=metrics,
        )
    if rain > 5.0 or wind > 8.0 or gust > 12.0:
        return WeatherAssessment(
            risk="caution",
            reason="Conditions dégradées (pluie modérée/rafales) — marges requises",
            metrics=metrics,
        )
    return WeatherAssessment(
        risk="safe",
        reason="Conditions nominales",
        metrics=metrics,
    )


def check_weather(lat: float, lon: float) -> WeatherAssessment:
    metrics = fetch_weather(lat, lon)
    return assess_weather(metrics)

