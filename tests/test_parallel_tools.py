"""
Integration test: parallel vs sequential tool calls with real APIs.
Verifies that asyncio.gather actually speeds things up with real HTTP.

Run from backend/: python -m pytest ../tests/test_parallel_tools.py -v -s
"""
import asyncio
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from tools.search import langsearch

QUERIES = [
    "San Francisco Mission District coffee shops locals love",
    "San Francisco free outdoor parks hiking trails worth visiting",
    "San Francisco affordable brunch spots locals recommend under $20",
]


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def run_sequential(queries):
    results = []
    for q in queries:
        r = await langsearch(q)
        results.append(r)
    return results


async def run_parallel(queries):
    return await asyncio.gather(*[langsearch(q) for q in queries])


class TestParallelLangsearch:

    def test_parallel_returns_same_count(self):
        """Parallel fetch returns one result per query."""
        results = run(run_parallel(QUERIES))
        assert len(results) == len(QUERIES)

    def test_each_result_has_results(self):
        """Each search returns at least one result."""
        results = run(run_parallel(QUERIES))
        for r in results:
            assert "results" in r
            assert len(r["results"]) > 0

    def test_parallel_faster_than_sequential(self):
        """
        Parallel should finish significantly faster than sequential.
        Each HTTP call takes ~0.5-2s. Running 3 in parallel should be
        close to 1x the slowest call, not 3x the total.
        """
        # Sequential
        t0 = time.perf_counter()
        run(run_sequential(QUERIES))
        sequential_time = time.perf_counter() - t0

        # Parallel
        t0 = time.perf_counter()
        run(run_parallel(QUERIES))
        parallel_time = time.perf_counter() - t0

        speedup = sequential_time / parallel_time
        print(f"\n  Sequential: {sequential_time:.2f}s")
        print(f"  Parallel:   {parallel_time:.2f}s")
        print(f"  Speedup:    {speedup:.1f}x")

        # Parallel should be at least 1.5x faster than sequential
        assert speedup >= 1.5, (
            f"Expected parallel speedup >= 1.5x, got {speedup:.1f}x. "
            f"Sequential: {sequential_time:.2f}s, Parallel: {parallel_time:.2f}s"
        )

    def test_result_content_not_empty(self):
        """Results should have non-empty title and content."""
        results = run(run_parallel(QUERIES))
        for r in results:
            for item in r["results"]:
                assert item["title"]
                assert item["content"]
                assert item["url"]
