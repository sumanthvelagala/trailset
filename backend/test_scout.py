"""Test the scout node via the LangGraph graph."""
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv("../.env")

from graph import trip_graph


async def main():
    print("\nRunning Scout Agent via LangGraph...\n")

    result = await trip_graph.ainvoke({
        "city": "Austin",
        "date": "Saturday",
        "budget": 100.0,
        "vibe": "outdoors + good coffee, no tourist traps",
        "candidates": [],
        "stops": [],
        "eval_scores": {},
        "trajectory": [],
    })

    traj = result["trajectory"][0]
    print(f"Searches used:       {traj['searches_used']}")
    print(f"Tool calls:")
    for tc in traj["tool_calls"]:
        print(f"  → search: '{tc['query']}' ({tc['results_count']} results)")
    print(f"Candidates returned: {traj['candidates_returned']}")
    print(f"Tokens used:         {traj['tokens']}")
    print(f"Latency:             {traj['latency_ms']}ms")

    print("\nCandidates:")
    for i, c in enumerate(result["candidates"], 1):
        print(f"  {i}. {c['name']} ({c['type']}) — ${c['est_cost']} — {c['neighborhood']}")
        print(f"     {c['description']}")


if __name__ == "__main__":
    asyncio.run(main())
