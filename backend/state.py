from typing import TypedDict, Annotated
import operator


class TripState(TypedDict):
    # Input — set once by main.py
    city: str
    date: str
    budget: float
    vibe: str

    # Scout output
    candidates: list[dict]

    # Planner output
    stops: list[dict]

    # Eval output
    eval_scores: dict

    # Each node appends its log entry — Annotated[..., operator.add] means
    # LangGraph merges by concatenation instead of overwriting
    trajectory: Annotated[list[dict], operator.add]
