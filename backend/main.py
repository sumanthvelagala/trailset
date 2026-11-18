import time
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models import TripRequest, TripResponse, Observability, EvalScores
from agents.scout import run_scout
from agents.planner import run_planner
from evals.rule_based import run_rule_evals
from evals.llm_judge import run_llm_evals

load_dotenv()

app = FastAPI(title="Trailset API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/plan", response_model=TripResponse)
async def plan_trip(request: TripRequest):
    total_start = time.time()

    # Scout Agent
    scout_start = time.time()
    scout_result = await run_scout(request)
    scout_latency = int((time.time() - scout_start) * 1000)

    # Planner Agent
    planner_start = time.time()
    planner_result = await run_planner(request, scout_result.candidates)
    planner_latency = int((time.time() - planner_start) * 1000)

    total_latency = int((time.time() - total_start) * 1000)

    # Evals
    rule_evals = run_rule_evals(request, planner_result.stops)
    llm_evals = await run_llm_evals(request, planner_result.stops)

    total_cost = sum(s.est_cost for s in planner_result.stops)
    total_tokens = scout_result.tokens + planner_result.tokens
    # Gemini 2.5 Flash: ~$0.075 per 1M tokens
    estimated_cost = round(total_tokens * 0.075 / 1_000_000, 6)

    return TripResponse(
        stops=planner_result.stops,
        total_cost=total_cost,
        budget=request.budget,
        observability=Observability(
            scout_latency_ms=scout_latency,
            planner_latency_ms=planner_latency,
            total_latency_ms=total_latency,
            tavily_searches=scout_result.searches_used,
            input_tokens=scout_result.tokens + planner_result.tokens,
            output_tokens=0,  # tracked via total_tokens
            estimated_cost_usd=estimated_cost,
            eval_scores=EvalScores(
                **rule_evals,
                vibe_match=llm_evals.get("vibe_match"),
                relevance=llm_evals.get("relevance"),
            ),
        ),
    )
