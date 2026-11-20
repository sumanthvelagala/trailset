"""
Redis-backed trip result storage.
Stores full pipeline results and maintains a recent-runs list.
Gracefully no-ops if REDIS_URL is not set (local dev without Redis).
"""
import os
import json
import uuid
from datetime import datetime, timezone

import redis.asyncio as redis

RECENT_KEY = "trips:recent"
MAX_RECENT = 20
TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _client() -> redis.Redis | None:
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    return redis.from_url(url, decode_responses=True)


async def save_trip(city: str, vibe: str, budget: float, date: str, result: dict) -> str | None:
    """
    Save a trip result. Returns the trip ID, or None if Redis is unavailable.
    result should be the full TripResponse as a dict.
    """
    r = _client()
    if not r:
        return None

    trip_id = str(uuid.uuid4())
    entry = {
        "id": trip_id,
        "city": city,
        "vibe": vibe,
        "budget": budget,
        "date": date,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }

    try:
        async with r:
            pipe = r.pipeline()
            pipe.set(f"trip:{trip_id}", json.dumps(entry), ex=TTL_SECONDS)
            pipe.lpush(RECENT_KEY, trip_id)
            pipe.ltrim(RECENT_KEY, 0, MAX_RECENT - 1)
            await pipe.execute()
    except Exception:
        return None

    return trip_id


async def get_recent(limit: int = 10) -> list[dict]:
    """
    Return the most recent trip summaries (no full result payload).
    Returns [] if Redis is unavailable.
    """
    r = _client()
    if not r:
        return []

    try:
        async with r:
            ids = await r.lrange(RECENT_KEY, 0, limit - 1)
            if not ids:
                return []

            pipe = r.pipeline()
            for trip_id in ids:
                pipe.get(f"trip:{trip_id}")
            raw_entries = await pipe.execute()

        summaries = []
        for raw in raw_entries:
            if not raw:
                continue
            entry = json.loads(raw)
            result = entry.get("result", {})
            stops = result.get("stops", [])
            summaries.append({
                "id": entry["id"],
                "city": entry["city"],
                "vibe": entry["vibe"],
                "budget": entry["budget"],
                "date": entry["date"],
                "created_at": entry["created_at"],
                "stop_count": len(stops),
                "total_cost": result.get("total_cost", 0),
                "stop_names": [s["name"] for s in stops[:4]],
            })
        return summaries

    except Exception:
        return []


async def get_trip(trip_id: str) -> dict | None:
    """Return the full trip entry by ID, or None."""
    r = _client()
    if not r:
        return None

    try:
        async with r:
            raw = await r.get(f"trip:{trip_id}")
        return json.loads(raw) if raw else None
    except Exception:
        return None
