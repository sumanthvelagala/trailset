from typing import TypedDict, Annotated, Optional
import operator


class TripState(TypedDict):
    # Input — set once by main.py
    city: str
    date: str
    budget: float
    vibe: str
    start_location: Optional[str]   # e.g. "downtown Austin hotel" — optional
    start_coords: Optional[dict]    # {"lat": float, "lng": float} — geocoded from start_location

    # Scout output
    candidates: list[dict]

    # Planner output
    stops: list[dict]

    # Enrich output — all candidates with real hours + prices + lat/lng added
    enriched_candidates: list[dict]

    # Eval output
    eval_scores: dict

    # Each node appends its log — operator.add means LangGraph concatenates
    trajectory: Annotated[list[dict], operator.add]

    # Retry tracking
    scout_retries: int
    planner_retries: int
    retry_feedback: str   # passed back to agent explaining what to fix

    # Set if max retries exceeded
    error: Optional[str]
