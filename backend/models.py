from pydantic import BaseModel
from typing import Optional


class TripRequest(BaseModel):
    city: str
    date: str
    budget: float
    vibe: str


class Candidate(BaseModel):
    name: str
    type: str  # coffee, food, outdoor_activity, park, market
    neighborhood: str
    est_cost: float
    description: str


class Stop(BaseModel):
    name: str
    type: str
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    start_time: str
    dwell_min: int
    travel_to_next_min: int
    est_cost: float
    vibe_reason: str


class EvalScores(BaseModel):
    budget_ok: bool
    city_ok: bool
    schedule_ok: bool
    stop_count_ok: bool
    vibe_match: Optional[float] = None
    relevance: Optional[float] = None


class Observability(BaseModel):
    scout_latency_ms: int
    planner_latency_ms: int
    total_latency_ms: int
    tavily_searches: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    eval_scores: EvalScores


class TripResponse(BaseModel):
    stops: list[Stop]
    total_cost: float
    budget: float
    observability: Observability
