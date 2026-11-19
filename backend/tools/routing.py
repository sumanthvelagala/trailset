import os
import math
import httpx


def _haversine_minutes(lat1: float, lng1: float, lat2: float, lng2: float) -> tuple[float, str]:
    """Fallback distance estimate using Haversine formula."""
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    miles = R * 2 * math.asin(math.sqrt(a))

    if miles < 0.5:
        return round(miles / 3 * 60), "walk"   # ~3 mph walking
    return round(miles / 25 * 60), "drive"     # ~25 mph city driving


async def travel_time(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
    departure_time: str,   # ISO 8601 e.g. "2025-11-22T09:00:00"
) -> dict:
    """
    Get travel time between two points using HERE Routing API.
    Auto-selects walk vs drive based on distance.
    Falls back to Haversine estimate if HERE fails.
    Returns {"minutes": int, "mode": str, "source": str}
    """
    # Determine mode by straight-line distance first
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    miles = R * 2 * math.asin(math.sqrt(a))
    mode = "pedestrian" if miles < 0.5 else "car"
    mode_label = "walk" if mode == "pedestrian" else "drive"

    api_key = os.getenv("HERE_API_KEY")
    if not api_key:
        mins, _ = _haversine_minutes(lat1, lng1, lat2, lng2)
        return {"minutes": mins, "mode": mode_label, "source": "haversine_fallback"}

    url = "https://router.hereapi.com/v8/routes"
    params = {
        "apiKey": api_key,
        "origin": f"{lat1},{lng1}",
        "destination": f"{lat2},{lng2}",
        "transportMode": mode,
        "departureTime": departure_time,
        "return": "summary",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        seconds = data["routes"][0]["sections"][0]["summary"]["duration"]
        return {"minutes": round(seconds / 60), "mode": mode_label, "source": "here_api"}

    except Exception:
        mins, _ = _haversine_minutes(lat1, lng1, lat2, lng2)
        return {"minutes": mins, "mode": mode_label, "source": "haversine_fallback"}
