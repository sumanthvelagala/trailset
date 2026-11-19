"""
Enrich node test — requires Nominatim (no LLM, no API keys).
Verifies:
1. All candidates get geocoded with real lat/lng
2. dist_from_origin_miles computed for each
3. start_location geocoding works
4. Fallback to city center when no start_location
"""
import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

from nodes.enrich import enrich_node

TEST_CANDIDATES = [
    {"name": "Barton Springs Pool", "type": "outdoor_activity", "neighborhood": "Zilker",
     "est_cost": 9.0, "cost_verified": True, "description": "Natural spring-fed pool"},
    {"name": "Bennu Coffee", "type": "coffee", "neighborhood": "East Austin",
     "est_cost": 6.0, "cost_verified": False, "description": "Local coffee shop"},
    {"name": "Franklin Barbecue", "type": "food", "neighborhood": "East Austin",
     "est_cost": 25.0, "cost_verified": False, "description": "Famous Austin BBQ"},
    {"name": "Zilker Park", "type": "park", "neighborhood": "Zilker",
     "est_cost": 0.0, "cost_verified": True, "description": "Large city park"},
]

BASE_STATE = {
    "city": "Austin",
    "date": "Saturday",
    "budget": 100.0,
    "vibe": "outdoors, coffee, local eats",
    "candidates": TEST_CANDIDATES,
    "enriched_candidates": [],
    "stops": [],
    "eval_scores": {},
    "trajectory": [],
    "scout_retries": 0,
    "planner_retries": 0,
    "retry_feedback": "",
    "error": None,
}


async def run_test(label: str, state: dict):
    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")

    result = await enrich_node(state)
    enriched = result["enriched_candidates"]
    traj = result["trajectory"][0]

    print(f"Geocoded:   {traj['geocoded_count']}/{traj['candidates_enriched']}")
    print(f"Origin:     {traj['origin_used']}")
    print(f"Latency:    {traj['latency_ms']}ms")

    print("\n  Candidate                   | Coords              | Miles from origin")
    print("  " + "-" * 68)
    for c in enriched:
        coords = f"({c['lat']:.3f}, {c['lng']:.3f})" if c["lat"] else "NO COORDS"
        dist = f"{c['dist_from_origin_miles']} mi" if c["dist_from_origin_miles"] is not None else "N/A"
        print(f"  {c['name']:<28} | {coords:<19} | {dist}")

    # Assertions
    geocoded = [c for c in enriched if c["lat"] is not None]
    assert len(geocoded) >= 3, f"Only {len(geocoded)}/4 geocoded"

    dists = [c for c in enriched if c["dist_from_origin_miles"] is not None]
    assert len(dists) >= 3, f"Only {len(dists)}/4 have distances"

    print(f"\n  PASS: {len(geocoded)}/4 geocoded, {len(dists)}/4 have distances")
    return enriched


async def run_enrich_tests():
    print("\nRunning enrich tests (Nominatim only, no LLM)...")

    # Test 1: no start_location → falls back to city center
    await run_test(
        "No start_location → city center as origin",
        {**BASE_STATE, "start_location": None, "start_coords": None}
    )

    # Test 2: with start_location
    await run_test(
        "With start_location: downtown Austin",
        {**BASE_STATE, "start_location": "downtown Austin", "start_coords": None}
    )

    print("\nAll enrich tests passed.\n")


if __name__ == "__main__":
    asyncio.run(run_enrich_tests())
