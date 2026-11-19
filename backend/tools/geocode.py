import os
import httpx


async def geocode(place_name: str, city: str, use_here: bool = True) -> dict:
    """
    Geocode a place name. HERE is primary, Nominatim is fallback.
    Set use_here=False to skip HERE and go directly to Nominatim (for cap enforcement).
    Returns {"lat": float, "lng": float} or {"lat": None, "lng": None} on failure.
    """
    if use_here:
        result = await _here_geocode(place_name, city)
        if result["lat"] is not None:
            return result
    return await _nominatim_geocode(place_name, city)


async def _here_geocode(place_name: str, city: str) -> dict:
    api_key = os.getenv("HERE_API_KEY")
    if not api_key:
        return {"lat": None, "lng": None}

    url = "https://geocode.search.hereapi.com/v1/geocode"
    params = {"q": f"{place_name}, {city}", "apiKey": api_key, "limit": 1}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        items = data.get("items", [])
        if items:
            pos = items[0]["position"]
            return {"lat": pos["lat"], "lng": pos["lng"]}
    except Exception:
        pass

    return {"lat": None, "lng": None}


async def _nominatim_geocode(place_name: str, city: str) -> dict:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": f"{place_name}, {city}", "format": "json", "limit": 1}
    headers = {"User-Agent": "Trailset/1.0 (trip planner app)"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            results = response.json()

        if results:
            return {"lat": float(results[0]["lat"]), "lng": float(results[0]["lon"])}
    except Exception:
        pass

    return {"lat": None, "lng": None}
