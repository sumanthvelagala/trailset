"""
Run specific city/vibe combinations through the full pipeline and store results in Redis.
Run this manually to populate the home page examples.

Usage:
  python run_examples.py                 # run all combinations below
  python run_examples.py "San Francisco" # run only entries matching that city
"""
import asyncio
import json
import sys
from dotenv import load_dotenv
load_dotenv("../.env")

from graph import trip_graph
from store import save_trip

COMBINATIONS = [
    {
        "city": "San Francisco",
        "vibe": "coffee, brunch, street art, local vibes",
        "budget": 80,
        "date": "Saturday",
    },
    {
        "city": "Austin",
        "vibe": "outdoors, good coffee, no tourist traps",
        "budget": 60,
        "date": "Saturday",
    },
    {
        "city": "New York",
        "vibe": "jazz bars, brunch, Brooklyn local spots",
        "budget": 80,
        "date": "Saturday",
    },
    {
        "city": "Portland",
        "vibe": "vegan food, bookshops, parks",
        "budget": 50,
        "date": "Saturday",
    },
    {
        "city": "Nashville",
        "vibe": "honky tonk, hot chicken, murals",
        "budget": 60,
        "date": "Saturday",
    },
    {
        "city": "Chicago",
        "vibe": "deep dish, architecture, lakefront",
        "budget": 70,
        "date": "Saturday",
    },
]


async def run_one(combo: dict) -> None:
    city = combo["city"]
    vibe = combo["vibe"]
    budget = combo["budget"]
    date = combo["date"]

    print(f"\n{'='*55}")
    print(f"  {city} — {vibe} — ${budget}")
    print(f"{'='*55}")

    result = await trip_graph.ainvoke({
        "city": city,
        "date": date,
        "budget": budget,
        "vibe": vibe,
        "start_location": None,
        "start_coords": None,
        "candidates": [],
        "enriched_candidates": [],
        "stops": [],
        "eval_scores": {},
        "trajectory": [],
        "scout_retries": 0,
        "planner_retries": 0,
        "retry_feedback": "",
        "error": None,
    })

    if result.get("error"):
        print(f"  ERROR: {result['error']}")
        return

    stops = result.get("stops", [])
    total_cost = sum(s["est_cost"] for s in stops)
    scores = result.get("eval_scores", {})

    print(f"  Stops ({len(stops)}):")
    for s in stops:
        web = len(s.get("source_urls", []))
        yt  = len(s.get("source_videos", []))
        print(f"    {s['start_time']}  {s['name']} (${s['est_cost']}) [{web} web, {yt} yt]")
    print(f"  Total: ${total_cost:.0f}  |  vibe={scores.get('vibe_match')}  relevance={scores.get('relevance')}  passed={scores.get('passed')}")

    # Serialize stops for storage (convert to plain dicts)
    result_payload = {
        "stops": stops,
        "total_cost": total_cost,
        "budget": budget,
        "eval_scores": scores,
        "observability": {
            "total_latency_ms": sum(t.get("latency_ms", 0) for t in result.get("trajectory", [])),
            "tavily_searches": 0,
            "route_calls": sum(t.get("route_calls", 0) for t in result.get("trajectory", []) if t.get("node") == "planner"),
            "total_tokens": sum(t.get("tokens", 0) for t in result.get("trajectory", [])),
            "estimated_cost_usd": 0,
            "trajectory": result.get("trajectory", []),
        },
    }

    trip_id = await save_trip(city, vibe, budget, date, result_payload)
    if trip_id:
        print(f"  Saved → trip:{trip_id}")
    else:
        print(f"  Not saved (REDIS_URL not set)")


async def main():
    filter_city = sys.argv[1].lower() if len(sys.argv) > 1 else None
    combos = [c for c in COMBINATIONS if not filter_city or filter_city in c["city"].lower()]

    print(f"Running {len(combos)} combination(s)...")
    for combo in combos:
        await run_one(combo)

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
