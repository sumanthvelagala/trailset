import time
import math
import asyncio

from state import TripState
from tools.geocode import geocode
from config import MAX_GEOCODE_CALLS


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return round(R * 2 * math.asin(math.sqrt(a)), 2)


async def enrich_node(state: TripState) -> dict:
    """
    Pre-processing step before planner:
    1. Geocodes all scout candidates concurrently (Nominatim)
    2. Geocodes start_location if provided, otherwise geocodes city center
    3. Computes Haversine distance from start/center to each candidate
       so planner can reason about geography without calling any tools
    No LLM calls — pure deterministic lookups.
    """
    start = time.time()
    candidates = state["candidates"]
    city = state["city"]

    # Geocode all candidates + origin, capping HERE calls at MAX_GEOCODE_CALLS.
    # First MAX_GEOCODE_CALLS use HERE (accurate), rest fall back to Nominatim.
    here_budget = MAX_GEOCODE_CALLS  # includes origin call

    origin_use_here = here_budget > 0
    here_budget -= 1

    candidate_tasks = []
    for i, c in enumerate(candidates):
        use_here = i < here_budget
        candidate_tasks.append(geocode(c["name"], city, use_here=use_here))

    if state.get("start_location"):
        origin_task = geocode(state["start_location"], city, use_here=origin_use_here)
    else:
        origin_task = geocode(city, city, use_here=origin_use_here)

    all_results = await asyncio.gather(*candidate_tasks, origin_task)
    geo_results = all_results[:-1]
    origin_coords = all_results[-1]

    # Fallback: if origin geocoding failed use first successfully geocoded candidate
    if origin_coords["lat"] is None:
        for r in geo_results:
            if r["lat"] is not None:
                origin_coords = r
                break

    # Build enriched candidates with coords + distance from origin
    enriched = []
    for candidate, coords in zip(candidates, geo_results):
        enriched_candidate = {**candidate, "lat": coords["lat"], "lng": coords["lng"]}
        if coords["lat"] is not None and origin_coords["lat"] is not None:
            enriched_candidate["dist_from_origin_miles"] = _haversine_miles(
                origin_coords["lat"], origin_coords["lng"],
                coords["lat"], coords["lng"]
            )
        else:
            enriched_candidate["dist_from_origin_miles"] = None
        enriched.append(enriched_candidate)

    # Resolve start_coords for state
    start_coords = None
    if state.get("start_location") and origin_coords["lat"] is not None:
        start_coords = origin_coords

    geocoded_count = sum(1 for c in enriched if c["lat"] is not None)
    latency_ms = int((time.time() - start) * 1000)

    return {
        "enriched_candidates": enriched,
        "start_coords": start_coords,
        "trajectory": [{
            "node": "enrich",
            "candidates_enriched": len(enriched),
            "geocoded_count": geocoded_count,
            "start_location_geocoded": start_coords is not None,
            "origin_used": state.get("start_location") or city,
            "latency_ms": latency_ms,
        }],
    }
