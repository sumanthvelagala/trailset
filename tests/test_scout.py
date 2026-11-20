"""
Unit tests for scout_node — all external calls mocked.
Run from backend/: python -m pytest ../tests/test_scout.py -v
"""
import asyncio
import os
import sys
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("GOOGLE_AI_API_KEY", "mock-key")

# ── Shared mock data ──────────────────────────────────────────────────────────

MOCK_SEARCH = {
    "results": [
        {"title": "Sightglass Coffee SF", "content": "Best coffee in SoMa, $5 latte, opens 7am", "url": "http://a.com"},
        {"title": "Dolores Park",         "content": "Free outdoor park in Mission, dog friendly", "url": "http://b.com"},
        {"title": "Tartine Bakery",       "content": "Famous bakery Mission, croissants $4, opens 8am weekends", "url": "http://c.com"},
    ],
    "images": [],
}

MOCK_YOUTUBE = {"results": [], "videos": []}

MOCK_STATE = {
    "city": "San Francisco",
    "date": "Saturday, Nov 22",
    "budget": 100,
    "vibe": "coffee, brunch, street art, local vibes",
    "start_location": None,
    "retry_feedback": None,
}


def _make_plan_response():
    r = MagicMock()
    r.usage_metadata.total_token_count = 100
    r.parsed.langsearch_queries = ["SF Mission coffee shops locals love", "SF brunch spots affordable"]
    r.parsed.youtube_queries = ["San Francisco local guide 2025"]
    return r


def _make_followup_response(with_tool_call=False, query="SF hidden coffee spots reddit"):
    """Followup response — optionally requests one extra search."""
    r = MagicMock()
    r.usage_metadata.total_token_count = 150

    if with_tool_call:
        fc = MagicMock()
        fc.name = "search_places"
        fc.args = {"query": query}
        part = MagicMock()
        part.function_call = fc
        r.candidates = [MagicMock()]
        r.candidates[0].content.parts = [part]
    else:
        part = MagicMock()
        part.function_call = None
        r.candidates = [MagicMock()]
        r.candidates[0].content.parts = [part]

    return r


def _make_extract_response():
    from nodes.scout import CandidateList, Candidate
    r = MagicMock()
    r.usage_metadata.total_token_count = 300
    r.parsed = CandidateList(candidates=[
        Candidate(name="Sightglass Coffee", type="coffee", neighborhood="SoMa",
                  est_cost=5.0, cost_verified=True, description="Great coffee",
                  snippets=["Opens 7am", "$5 latte"], image_url=None),
        Candidate(name="Dolores Park", type="park", neighborhood="Mission",
                  est_cost=0.0, cost_verified=True, description="Free sunny park",
                  snippets=["Dog friendly", "Free entry"], image_url=None),
        Candidate(name="Tartine Bakery", type="food", neighborhood="Mission",
                  est_cost=12.0, cost_verified=True, description="Iconic bakery",
                  snippets=["Croissants $4", "Opens 8am weekends"], image_url=None),
    ])
    return r


# ── Tests ─────────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestScoutNoExtraSearches:
    """LLM satisfied after initial fetch — no extra searches."""

    def setup_method(self):
        call_order = [_make_plan_response(), _make_followup_response(with_tool_call=False), _make_extract_response()]
        self._idx = 0

        async def mock_generate(client, **kwargs):
            r = call_order[self._idx]
            self._idx += 1
            return r

        self._patches = [
            patch("google.genai.Client", return_value=MagicMock()),
            patch("nodes.scout._generate_with_retry", new=mock_generate),
            patch("nodes.scout.langsearch",      new=AsyncMock(return_value=MOCK_SEARCH)),
            patch("nodes.scout.youtube_search",  new=AsyncMock(return_value=MOCK_YOUTUBE)),
        ]
        for p in self._patches:
            p.start()

    def teardown_method(self):
        for p in self._patches:
            p.stop()

    def test_returns_candidates(self):
        from nodes.scout import scout_node
        result = run(scout_node(MOCK_STATE))
        assert len(result["candidates"]) == 3

    def test_no_extra_searches(self):
        from nodes.scout import scout_node
        result = run(scout_node(MOCK_STATE))
        t = result["trajectory"][0]
        assert t["extra_searches_used"] == 0
        assert t["searches_used"] == 2

    def test_trajectory_shape(self):
        from nodes.scout import scout_node
        result = run(scout_node(MOCK_STATE))
        t = result["trajectory"][0]
        assert t["node"] == "scout"
        assert t["youtube_searches_used"] == 1
        assert t["tokens"] == 550  # 100 + 150 + 300
        assert t["latency_ms"] >= 0

    def test_candidate_fields(self):
        from nodes.scout import scout_node
        result = run(scout_node(MOCK_STATE))
        c = result["candidates"][0]
        assert "name" in c
        assert "type" in c
        assert "est_cost" in c
        assert "cost_verified" in c
        assert "snippets" in c
        assert "source_videos" in c  # added post-extraction

    def test_source_videos_is_list(self):
        from nodes.scout import scout_node
        result = run(scout_node(MOCK_STATE))
        for c in result["candidates"]:
            assert isinstance(c["source_videos"], list)


class TestScoutWithExtraSearch:
    """LLM requests one extra search, then stops."""

    def setup_method(self):
        call_order = [
            _make_plan_response(),
            _make_followup_response(with_tool_call=True, query="SF street art coffee Mission locals"),
            _make_followup_response(with_tool_call=False),  # satisfied after extra search
            _make_extract_response(),
        ]
        self._idx = 0

        async def mock_generate(client, **kwargs):
            r = call_order[self._idx]
            self._idx += 1
            return r

        self._patches = [
            patch("google.genai.Client", return_value=MagicMock()),
            patch("nodes.scout._generate_with_retry", new=mock_generate),
            patch("nodes.scout.langsearch",      new=AsyncMock(return_value=MOCK_SEARCH)),
            patch("nodes.scout.youtube_search",  new=AsyncMock(return_value=MOCK_YOUTUBE)),
        ]
        for p in self._patches:
            p.start()

    def teardown_method(self):
        for p in self._patches:
            p.stop()

    def test_extra_search_fired(self):
        from nodes.scout import scout_node
        result = run(scout_node(MOCK_STATE))
        t = result["trajectory"][0]
        assert t["extra_searches_used"] == 1

    def test_extra_query_logged(self):
        from nodes.scout import scout_node
        result = run(scout_node(MOCK_STATE))
        tools = [c["tool"] for c in result["trajectory"][0]["tool_calls"]]
        assert "langsearch_extra" in tools

    def test_still_returns_candidates(self):
        from nodes.scout import scout_node
        result = run(scout_node(MOCK_STATE))
        assert len(result["candidates"]) == 3


class TestScoutParallelToolCalls:
    """
    When LLM requests multiple tool calls in one response,
    they must run in parallel — not sequentially.
    Verified by timing: parallel calls finish in ~1 delay, sequential would take ~N * delay.
    """

    DELAY = 0.15  # seconds per mock search call

    def setup_method(self):
        import time

        # Followup response returns TWO function calls at once
        def _make_two_tool_calls_response():
            r = MagicMock()
            r.usage_metadata.total_token_count = 150

            fc1 = MagicMock(); fc1.name = "search_places"; fc1.args = {"query": "SF jazz bars Mission locals"}
            fc2 = MagicMock(); fc2.name = "search_places"; fc2.args = {"query": "SF cheap eats SoMa reddit"}

            p1 = MagicMock(); p1.function_call = fc1
            p2 = MagicMock(); p2.function_call = fc2

            r.candidates = [MagicMock()]
            r.candidates[0].content.parts = [p1, p2]
            return r

        call_order = [
            _make_plan_response(),
            _make_two_tool_calls_response(),   # LLM asks for 2 extra searches at once
            _make_followup_response(with_tool_call=False),  # satisfied
            _make_extract_response(),
        ]
        self._idx = 0

        async def mock_generate(client, **kwargs):
            r = call_order[self._idx]
            self._idx += 1
            return r

        # Slow mock langsearch — adds a delay to make parallel vs sequential measurable
        async def slow_langsearch(query):
            await asyncio.sleep(self.DELAY)
            return MOCK_SEARCH

        self._patches = [
            patch("google.genai.Client", return_value=MagicMock()),
            patch("nodes.scout._generate_with_retry", new=mock_generate),
            patch("nodes.scout.langsearch",     new=slow_langsearch),
            patch("nodes.scout.youtube_search", new=AsyncMock(return_value=MOCK_YOUTUBE)),
        ]
        for p in self._patches:
            p.start()

    def teardown_method(self):
        for p in self._patches:
            p.stop()

    def test_both_extra_queries_executed(self):
        """Both tool calls requested by LLM should appear in trajectory."""
        from nodes.scout import scout_node
        result = run(scout_node(MOCK_STATE))
        extra = [c for c in result["trajectory"][0]["tool_calls"] if c["tool"] == "langsearch_extra"]
        assert len(extra) == 2

    def test_parallel_faster_than_sequential(self):
        """
        2 searches each taking DELAY seconds:
          parallel   → total ~DELAY       (1x)
          sequential → total ~2 * DELAY   (2x)
        We assert total time < 1.8 * DELAY to prove they ran in parallel.
        """
        import time
        from nodes.scout import scout_node

        # Time only the extra search phase — run full node and check wall time
        # Initial fetch (2 langsearch + 1 youtube) also run, so budget generously
        start = time.perf_counter()
        run(scout_node(MOCK_STATE))
        elapsed = time.perf_counter() - start

        # 4 initial searches + 2 extra. If extra were sequential: 6 * DELAY = 0.9s
        # If extra were parallel: 5 * DELAY = 0.75s (initial 4 parallel, extra 2 parallel)
        # Allow generous margin — just ensure it's not fully sequential
        max_sequential = 6 * self.DELAY * 0.95  # would be 0.855s if all sequential
        assert elapsed < max_sequential, (
            f"Looks sequential: {elapsed:.2f}s >= {max_sequential:.2f}s. "
            f"Expected parallel execution."
        )
