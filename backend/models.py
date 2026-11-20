from pydantic import BaseModel
from typing import Optional


class TripRequest(BaseModel):
    city: str
    date: str
    budget: float
    vibe: str
    start_location: Optional[str] = None


class StopOut(BaseModel):
    name: str
    type: str
    neighborhood: str
    start_time: str
    end_time: str
    dwell_minutes: int
    travel_to_next_minutes: int
    travel_mode: str
    est_cost: float
    cost_verified: bool
    lat: Optional[float] = None
    lng: Optional[float] = None
    reason: str
    snippets: list[str] = []
    source_videos: list[dict] = []
    source_urls: list[dict] = []
    image_url: Optional[str] = None


class EvalScores(BaseModel):
    budget_ok: bool
    stop_count_ok: bool
    schedule_ok: bool
    scout_coverage_ok: bool
    has_coords_ok: bool
    vibe_match: Optional[float] = None
    relevance: Optional[float] = None
    reasoning: Optional[str] = None
    passed: bool


class Observability(BaseModel):
    total_latency_ms: int
    tavily_searches: int
    route_calls: int
    total_tokens: int
    estimated_cost_usd: float
    trajectory: list[dict]


class TripResponse(BaseModel):
    stops: list[StopOut]
    total_cost: float
    budget: float
    eval_scores: EvalScores
    observability: Observability
