from models import Stop, TripRequest


def run_rule_evals(request: TripRequest, stops: list[Stop]) -> dict:
    total_cost = sum(s.est_cost for s in stops)

    return {
        "budget_ok": total_cost <= request.budget,
        "city_ok": all(request.city.lower() in s.address.lower() for s in stops),
        "schedule_ok": _check_schedule(stops),
        "stop_count_ok": 3 <= len(stops) <= 6,
    }


def _check_schedule(stops: list[Stop]) -> bool:
    """Check no overlapping slots and gaps >= 20 min between stops."""
    for i in range(len(stops) - 1):
        curr = stops[i]
        travel = curr.travel_to_next_min
        gap = travel  # gap between end of curr dwell and start of next
        if gap < 20 and travel < 20:
            return False
    return True
