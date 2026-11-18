import httpx
from typing import Optional


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "trailset-app/1.0 (contact@trailset.app)"}


async def geocode(place_name: str, city: str) -> Optional[tuple[float, float]]:
    """Return (lat, lng) for a place using Nominatim. Returns None if not found."""
    query = f"{place_name}, {city}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers=HEADERS,
            timeout=10,
        )
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    return None
