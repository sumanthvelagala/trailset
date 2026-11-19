"""
Grounding test — requires LLM + Tavily.
Verifies that scout candidates are traceable to actual search results,
not hallucinated by the model.
Runs 3 cities matching the golden test set.
"""
import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

from graph import trip_graph

GROUNDING_THRESHOLD = 0.7   # at least 70% of candidates must be traceable

TEST_CASES = [
    {
        "city": "Austin",
        "date": "Saturday",
        "budget": 100.0,
        "vibe": "outdoors, coffee, local eats. no tourist traps, dog friendly",
    },
    {
        "city": "NYC",
        "date": "Sunday",
        "budget": 60.0,
        "vibe": "art, brunch. no chains",
    },
    {
        "city": "Chicago",
        "date": "Saturday",
        "budget": 80.0,
        "vibe": "waterfront, local food",
    },
]


def check_grounding(candidates: list[dict], raw_search_results: list[dict]) -> dict:
    """
    For each candidate check if its name appears in any search result
    title or content. Returns grounding rate and per-candidate results.
    """
    corpus = []
    for entry in raw_search_results:
        for r in entry["results"]:
            corpus.append((r["title"] + " " + r["content"]).lower())

    results = []
    for c in candidates:
        name = c["name"].lower()
        name_parts = name.split()
        found = any(
            any(part in text for part in name_parts if len(part) > 3)
            for text in corpus
        )
        results.append({
            "name": c["name"],
            "type": c["type"],
            "grounded": found,
        })

    grounded_count = sum(1 for r in results if r["grounded"])
    rate = grounded_count / len(results) if results else 0

    return {
        "rate": rate,
        "grounded": grounded_count,
        "total": len(results),
        "per_candidate": results,
    }


async def run_single(tc: dict) -> bool:
    """Run grounding test for one city. Returns True if passed."""
    city = tc["city"]
    print(f"\n{'='*55}")
    print(f"  {city} | {tc['date']} | ${tc['budget']} | {tc['vibe']}")
    print(f"{'='*55}")

    result = await trip_graph.ainvoke({
        **tc,
        "candidates": [],
        "stops": [],
        "enriched_candidates": [],
        "eval_scores": {},
        "trajectory": [],
        "scout_retries": 0,
        "planner_retries": 0,
        "retry_feedback": "",
        "error": None,
    })

    scout_traj = result["trajectory"][0]
    candidates = result["candidates"]
    raw_results = scout_traj.get("raw_search_results", [])

    print(f"Searches run:   {scout_traj['searches_used']}")
    print(f"Candidates:     {len(candidates)}")
    print(f"Tokens used:    {scout_traj['tokens']}")
    print(f"Latency:        {scout_traj['latency_ms']}ms")

    grounding = check_grounding(candidates, raw_results)
    print(f"\nGrounding rate: {grounding['grounded']}/{grounding['total']} "
          f"({grounding['rate']:.0%})")

    for item in grounding["per_candidate"]:
        status = "GROUNDED" if item["grounded"] else "NOT FOUND"
        print(f"  [{status}] {item['name']} ({item['type']})")

    print("\n--- Queries used ---")
    for tc_log in scout_traj["tool_calls"]:
        print(f"  \"{tc_log['query']}\"  ({tc_log['results_count']} results)")

    passed = grounding["rate"] >= GROUNDING_THRESHOLD
    result_label = "PASS" if passed else "FAIL"
    print(f"\n{result_label}: grounding rate {grounding['rate']:.0%} "
          f"(threshold {GROUNDING_THRESHOLD:.0%})")
    return passed


async def run_grounding_tests():
    print(f"\nRunning grounding tests for {len(TEST_CASES)} cities (requires LLM + Tavily)...")

    results = []
    for tc in TEST_CASES:
        passed = await run_single(tc)
        results.append((tc["city"], passed))

    print(f"\n{'='*55}")
    print("SUMMARY")
    print(f"{'='*55}")
    for city, passed in results:
        label = "PASS" if passed else "FAIL"
        print(f"  [{label}] {city}")

    total_passed = sum(1 for _, p in results if p)
    print(f"\n{total_passed}/{len(results)} cities passed grounding threshold\n")

    assert total_passed == len(results), (
        f"{len(results) - total_passed} cities failed grounding check"
    )


if __name__ == "__main__":
    asyncio.run(run_grounding_tests())
