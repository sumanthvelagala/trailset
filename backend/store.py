"""
Redis-backed trip result storage using Upstash REST API.
Stores full pipeline results and maintains a recent-runs list.
Gracefully no-ops if UPSTASH_REDIS_REST_URL / TOKEN are not set.
"""
import os
import json
import uuid
from datetime import datetime, timezone

RECENT_KEY = "trips:recent"
MAX_RECENT = 20
TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _client():
    url = os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        return None
    from upstash_redis.asyncio import Redis
    return Redis(url=url, token=token)


async def save_trip(city: str, vibe: str, budget: float, date: str, result: dict) -> str | None:
    """Save a trip result. Returns trip ID, or None if Redis unavailable."""
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
        pipe = r.pipeline()
        pipe.set(f"trip:{trip_id}", json.dumps(entry), ex=TTL_SECONDS)
        pipe.lpush(RECENT_KEY, trip_id)
        pipe.ltrim(RECENT_KEY, 0, MAX_RECENT - 1)
        await pipe.exec()
    except Exception:
        return None

    return trip_id


async def get_recent(limit: int = 10) -> list[dict]:
    """Return most recent trip summaries. Returns [] if Redis unavailable."""
    r = _client()
    if not r:
        return []

    try:
        ids = await r.lrange(RECENT_KEY, 0, limit - 1)
        if not ids:
            return []

        pipe = r.pipeline()
        for trip_id in ids:
            pipe.get(f"trip:{trip_id}")
        raw_entries = await pipe.exec()

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
    """Return full trip entry by ID, or None."""
    r = _client()
    if not r:
        return None

    try:
        raw = await r.get(f"trip:{trip_id}")
        return json.loads(raw) if raw else None
    except Exception:
        return None
