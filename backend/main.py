import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

from models import TripRequest, TripResponse, StopOut, EvalScores, Observability
from graph import trip_graph
from store import get_recent, get_trip

load_dotenv()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Trailset API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "*")],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/recent")
async def recent_trips(limit: int = 6):
    return await get_recent(limit=limit)


@app.get("/trips/{trip_id}")
async def get_trip_by_id(trip_id: str):
    from fastapi import HTTPException
    entry = await get_trip(trip_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Trip not found")
    return entry


@app.post("/plan", response_model=TripResponse)
@limiter.limit("5/hour")
@limiter.limit("20/day")
async def plan_trip(request: Request, body: TripRequest):
    start = time.time()

    initial_state = {
        "city": body.city,
        "date": body.date,
        "budget": body.budget,
        "vibe": body.vibe,
        "start_location": body.start_location,
        "start_coords": None,
        "candidates": [],
        "enriched_candidates": [],
        "stops": [],
        "eval_scores": {},
        "trajectory": [],
        "scout_retries": 0,
        "planner_retries": 0,
        "retry_feedback": "",
        "error": None,
    }

    result = await trip_graph.ainvoke(initial_state)

    if result.get("error"):
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=result["error"])

    total_latency_ms = int((time.time() - start) * 1000)
    trajectory = result.get("trajectory", [])

    # Extract observability metrics from trajectory
    tavily_searches = sum(
        len(t.get("tool_calls", [])) for t in trajectory if t.get("node") == "scout"
    )
    route_calls = sum(
        t.get("route_calls", 0) for t in trajectory if t.get("node") == "planner"
    )
    total_tokens = sum(t.get("tokens", 0) for t in trajectory)
    # gemini-3.5-flash-lite: ~$0.10 per 1M tokens (input+output)
    estimated_cost_usd = round(total_tokens * 0.10 / 1_000_000, 6)

    stops_raw = result.get("stops", [])
    stops = [StopOut(**s) for s in stops_raw]
    total_cost = sum(s.est_cost for s in stops)

    eval_raw = result.get("eval_scores", {})
    eval_scores = EvalScores(
        budget_ok=eval_raw.get("budget_ok", False),
        stop_count_ok=eval_raw.get("stop_count_ok", False),
        schedule_ok=eval_raw.get("schedule_ok", False),
        scout_coverage_ok=eval_raw.get("scout_coverage_ok", False),
        has_coords_ok=eval_raw.get("has_coords_ok", False),
        vibe_match=eval_raw.get("vibe_match"),
        relevance=eval_raw.get("relevance"),
        reasoning=eval_raw.get("reasoning"),
        passed=eval_raw.get("passed", False),
    )

    return TripResponse(
        stops=stops,
        total_cost=total_cost,
        budget=body.budget,
        eval_scores=eval_scores,
        observability=Observability(
            total_latency_ms=total_latency_ms,
            tavily_searches=tavily_searches,
            route_calls=route_calls,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            trajectory=trajectory,
        ),
    )
