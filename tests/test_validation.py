"""
Validation tests — no LLM calls needed.
Tests graph routing: validate_scout, validate_planner, retry nodes, error handling.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from graph import validate_scout, retry_scout_node, validate_planner, retry_planner_node
from config import MAX_SCOUT_RETRIES, MAX_PLANNER_RETRIES


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_state(candidates=None, stops=None, scout_retries=0, planner_retries=0,
               retry_feedback="", budget=100.0):
    return {
        "city": "Austin", "date": "Saturday", "budget": budget,
        "vibe": "outdoors + coffee",
        "start_location": None, "start_coords": None,
        "candidates": candidates or [],
        "enriched_candidates": [],
        "stops": stops or [],
        "eval_scores": {}, "trajectory": [],
        "scout_retries": scout_retries,
        "planner_retries": planner_retries,
        "retry_feedback": retry_feedback,
        "error": None,
    }


def make_candidate(name="Place", i=0):
    return {"name": f"{name} {i}", "type": "coffee", "neighborhood": "X",
            "est_cost": 10.0, "cost_verified": False, "description": "desc",
            "snippets": [], "image_url": None}


def make_stop(name="Stop", cost=10.0, lat=30.26, lng=-97.77):
    return {"name": name, "type": "coffee", "neighborhood": "X",
            "start_time": "9:00 AM", "end_time": "9:35 AM",
            "dwell_minutes": 35, "travel_to_next_minutes": 10,
            "travel_mode": "drive", "est_cost": cost, "cost_verified": False,
            "lat": lat, "lng": lng, "reason": "fits vibe",
            "snippets": [], "image_url": None}


# ── Scout validation tests ────────────────────────────────────────────────────

def test_validate_scout_passes_with_enough_candidates():
    state = make_state(candidates=[make_candidate(i=i) for i in range(9)])
    assert validate_scout(state) == "planner"
    print("  PASS: 9 candidates → routes to planner")


def test_validate_scout_retries_when_too_few():
    state = make_state(candidates=[make_candidate(i=i) for i in range(3)])
    assert validate_scout(state) == "retry_scout"
    print("  PASS: 3 candidates → routes to retry_scout")


def test_validate_scout_retries_on_missing_fields():
    candidates = [{"name": "", "type": "coffee", "neighborhood": "X",
                   "est_cost": 10.0, "description": "desc"} for _ in range(9)]
    state = make_state(candidates=candidates)
    assert validate_scout(state) == "retry_scout"
    print("  PASS: missing name → routes to retry_scout")


def test_validate_scout_hits_error_after_max_retries():
    state = make_state(candidates=[make_candidate(i=i) for i in range(3)],
                       scout_retries=MAX_SCOUT_RETRIES)
    assert validate_scout(state) == "error"
    print(f"  PASS: {MAX_SCOUT_RETRIES} retries exceeded → routes to error")


def test_exactly_six_candidates_passes():
    state = make_state(candidates=[make_candidate(i=i) for i in range(6)])
    assert validate_scout(state) == "planner"
    print("  PASS: exactly 6 candidates → routes to planner")


def test_retry_scout_increments_counter():
    state = make_state(scout_retries=0)
    result = retry_scout_node(state)
    assert result["scout_retries"] == 1
    print("  PASS: scout retry counter incremented to 1")


def test_retry_scout_sets_feedback_for_too_few():
    state = make_state(candidates=[make_candidate(i=i) for i in range(3)],
                       scout_retries=0)
    result = retry_scout_node(state)
    assert "3" in result["retry_feedback"] and "6" in result["retry_feedback"]
    print(f"  PASS: scout feedback: '{result['retry_feedback']}'")


# ── Planner validation tests ──────────────────────────────────────────────────

def test_validate_planner_passes_with_valid_stops():
    stops = [make_stop(name=f"Stop {i}", cost=20.0) for i in range(4)]
    state = make_state(stops=stops, budget=100.0)
    assert validate_planner(state) == "eval"
    print("  PASS: 4 valid stops within budget → routes to eval")


def test_validate_planner_retries_too_few_stops():
    stops = [make_stop(name=f"Stop {i}") for i in range(2)]
    state = make_state(stops=stops)
    assert validate_planner(state) == "retry_planner"
    print("  PASS: 2 stops → routes to retry_planner")


def test_validate_planner_retries_over_budget():
    stops = [make_stop(name=f"Stop {i}", cost=40.0) for i in range(4)]
    state = make_state(stops=stops, budget=100.0)
    assert validate_planner(state) == "retry_planner"
    print("  PASS: $160 cost > $100 budget → routes to retry_planner")


def test_validate_planner_retries_missing_fields():
    stops = [{"name": "Stop", "type": "coffee"} for _ in range(4)]  # missing fields
    state = make_state(stops=stops, budget=100.0)
    assert validate_planner(state) == "retry_planner"
    print("  PASS: missing required fields → routes to retry_planner")


def test_validate_planner_hits_error_after_max_retries():
    stops = [make_stop(name=f"Stop {i}") for i in range(2)]
    state = make_state(stops=stops, planner_retries=MAX_PLANNER_RETRIES)
    assert validate_planner(state) == "error"
    print(f"  PASS: {MAX_PLANNER_RETRIES} planner retries exceeded → routes to error")


def test_retry_planner_increments_counter():
    state = make_state(planner_retries=0)
    result = retry_planner_node(state)
    assert result["planner_retries"] == 1
    print("  PASS: planner retry counter incremented to 1")


def test_retry_planner_feedback_too_few():
    stops = [make_stop(name=f"Stop {i}") for i in range(2)]
    state = make_state(stops=stops, planner_retries=0)
    result = retry_planner_node(state)
    assert "2" in result["retry_feedback"] and "3" in result["retry_feedback"]
    print(f"  PASS: planner feedback: '{result['retry_feedback']}'")


def test_retry_planner_feedback_over_budget():
    stops = [make_stop(name=f"Stop {i}", cost=40.0) for i in range(4)]
    state = make_state(stops=stops, budget=100.0, planner_retries=0)
    result = retry_planner_node(state)
    assert "160" in result["retry_feedback"] and "100" in result["retry_feedback"]
    print(f"  PASS: planner feedback: '{result['retry_feedback']}'")


def test_exactly_three_stops_passes():
    stops = [make_stop(name=f"Stop {i}", cost=20.0) for i in range(3)]
    state = make_state(stops=stops, budget=100.0)
    assert validate_planner(state) == "eval"
    print("  PASS: exactly 3 stops within budget → routes to eval")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scout_tests = [
        test_validate_scout_passes_with_enough_candidates,
        test_validate_scout_retries_when_too_few,
        test_validate_scout_retries_on_missing_fields,
        test_validate_scout_hits_error_after_max_retries,
        test_exactly_six_candidates_passes,
        test_retry_scout_increments_counter,
        test_retry_scout_sets_feedback_for_too_few,
    ]
    planner_tests = [
        test_validate_planner_passes_with_valid_stops,
        test_validate_planner_retries_too_few_stops,
        test_validate_planner_retries_over_budget,
        test_validate_planner_retries_missing_fields,
        test_validate_planner_hits_error_after_max_retries,
        test_retry_planner_increments_counter,
        test_retry_planner_feedback_too_few,
        test_retry_planner_feedback_over_budget,
        test_exactly_three_stops_passes,
    ]

    all_tests = scout_tests + planner_tests
    print(f"\nRunning {len(all_tests)} validation tests (no LLM)...\n")

    print("Scout:")
    passed = 0
    for t in scout_tests:
        try:
            t(); passed += 1
        except Exception as e:
            print(f"  FAIL: {t.__name__} — {e}")

    print("\nPlanner:")
    for t in planner_tests:
        try:
            t(); passed += 1
        except Exception as e:
            print(f"  FAIL: {t.__name__} — {e}")

    print(f"\n{passed}/{len(all_tests)} passed\n")
