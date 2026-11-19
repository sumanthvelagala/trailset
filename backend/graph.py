from langgraph.graph import StateGraph, END

from state import TripState
from nodes.scout import scout_node
from nodes.enrich import enrich_node
from nodes.planner import planner_node
from nodes.eval import eval_node
from config import MAX_SCOUT_RETRIES, MAX_PLANNER_RETRIES


def validate_scout(state: TripState) -> str:
    candidates = state.get("candidates", [])
    retries = state.get("scout_retries", 0)

    if retries >= MAX_SCOUT_RETRIES:
        return "error"

    if len(candidates) < 6:
        return "retry_scout"

    if not all(c.get("name") and c.get("type") for c in candidates):
        return "retry_scout"

    return "planner"  # planner node added Day 3


def retry_scout_node(state: TripState) -> dict:
    """Increment retry counter and set feedback before re-running scout."""
    candidates = state.get("candidates", [])
    retries = state.get("scout_retries", 0)

    if len(candidates) < 6:
        feedback = f"Only {len(candidates)} candidates returned. Need at least 6. Search more broadly with different queries."
    else:
        feedback = "Some candidates were missing required fields (name or type). Ensure all fields are populated."

    return {
        "scout_retries": retries + 1,
        "retry_feedback": feedback,
    }


def validate_planner(state: TripState) -> str:
    stops = state.get("stops", [])
    retries = state.get("planner_retries", 0)
    budget = state.get("budget", 0)

    if retries >= MAX_PLANNER_RETRIES:
        return "error"

    if len(stops) < 3:
        return "retry_planner"

    required = {"name", "type", "start_time", "end_time", "est_cost", "lat", "lng"}
    if not all(required.issubset(s.keys()) for s in stops):
        return "retry_planner"

    total_cost = sum(s.get("est_cost", 0) for s in stops)
    if total_cost > budget:
        return "retry_planner"

    return "eval"


def retry_planner_node(state: TripState) -> dict:
    stops = state.get("stops", [])
    retries = state.get("planner_retries", 0)
    budget = state.get("budget", 0)

    total_cost = sum(s.get("est_cost", 0) for s in stops)

    if len(stops) < 3:
        feedback = f"Only {len(stops)} stops returned. Need at least 3. Pick more stops from the candidates."
    elif total_cost > budget:
        feedback = f"Total cost ${total_cost:.0f} exceeds budget ${budget:.0f}. Pick cheaper stops or fewer stops."
    else:
        feedback = "Some stops are missing required fields (name, type, start_time, end_time, est_cost, lat, lng)."

    return {
        "planner_retries": retries + 1,
        "retry_feedback": feedback,
    }


def error_node(state: TripState) -> dict:
    return {"error": "Max retries exceeded. Could not generate enough candidates."}


def build_graph():
    graph = StateGraph(TripState)

    graph.add_node("scout", scout_node)
    graph.add_node("retry_scout", retry_scout_node)
    graph.add_node("enrich", enrich_node)
    graph.add_node("planner", planner_node)
    graph.add_node("retry_planner", retry_planner_node)
    graph.add_node("eval", eval_node)
    graph.add_node("failed", error_node)

    graph.set_entry_point("scout")

    graph.add_conditional_edges("scout", validate_scout, {
        "planner": "enrich",
        "retry_scout": "retry_scout",
        "error": "failed",
    })
    graph.add_conditional_edges("planner", validate_planner, {
        "eval": "eval",
        "retry_planner": "retry_planner",
        "error": "failed",
    })

    graph.add_edge("retry_scout", "scout")
    graph.add_edge("enrich", "planner")
    graph.add_edge("retry_planner", "planner")
    graph.add_edge("eval", END)
    graph.add_edge("failed", END)

    return graph.compile()


trip_graph = build_graph()
