from datetime import datetime


def run_rule_evals(state: dict) -> dict:
    stops = state.get("stops", [])
    candidates = state.get("candidates", [])
    budget = state.get("budget", 0)

    return {
        "budget_ok": _check_budget(stops, budget),
        "stop_count_ok": 3 <= len(stops) <= 6,
        "schedule_ok": _check_schedule(stops),
        "scout_coverage_ok": len(candidates) >= 6,
        "has_coords_ok": _check_coords(stops),
    }


def _check_budget(stops: list[dict], budget: float) -> bool:
    return sum(s.get("est_cost", 0) for s in stops) <= budget


def _check_schedule(stops: list[dict]) -> bool:
    """Check times are parseable and each stop ends before the next starts."""
    if len(stops) < 2:
        return True
    for i in range(len(stops) - 1):
        try:
            curr_end = datetime.strptime(stops[i]["end_time"], "%I:%M %p")
            next_start = datetime.strptime(stops[i + 1]["start_time"], "%I:%M %p")
            if curr_end > next_start:
                return False
        except (ValueError, KeyError):
            return False
    return True


def _check_coords(stops: list[dict]) -> bool:
    """At least 80% of stops have valid coordinates."""
    if not stops:
        return False
    with_coords = sum(1 for s in stops if s.get("lat") and s.get("lng"))
    return with_coords / len(stops) >= 0.8
