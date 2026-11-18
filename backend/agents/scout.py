import asyncio
import os
import time
from dataclasses import dataclass
from tavily import AsyncTavilyClient
import google.generativeai as genai
import json

from models import Candidate


@dataclass
class ScoutResult:
    candidates: list[Candidate]
    searches_used: int
    tokens: int


async def run_scout(request) -> ScoutResult:
    tavily = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    food_query = f"{request.city} best local coffee brunch lunch spots not touristy {request.vibe}"
    activity_query = f"{request.city} outdoor activities parks hidden gems {request.date} {request.vibe}"

    # Parallel searches
    food_task = tavily.search(food_query, max_results=5, search_depth="basic")
    activity_task = tavily.search(activity_query, max_results=5, search_depth="basic")
    food_results, activity_results = await asyncio.gather(food_task, activity_task)

    # Combine raw results for LLM to parse
    raw_food = "\n".join(
        f"- {r['title']}: {r['content'][:200]}" for r in food_results.get("results", [])
    )
    raw_activities = "\n".join(
        f"- {r['title']}: {r['content'][:200]}" for r in activity_results.get("results", [])
    )

    genai.configure(api_key=os.getenv("GOOGLE_AI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
You are a local travel scout. Based on the search results below, extract 8-10 real candidate places for a day trip.

City: {request.city}
Budget: ${request.budget}
Vibe: {request.vibe}

FOOD/COFFEE RESULTS:
{raw_food}

ACTIVITY RESULTS:
{raw_activities}

Return a JSON array of candidates. Each item:
{{
  "name": "place name",
  "type": "coffee|food|outdoor_activity|park|market",
  "neighborhood": "neighborhood or area",
  "est_cost": 0.0,
  "description": "one sentence why it fits the vibe"
}}

Only include places actually in {request.city}. Keep est_cost realistic. Return JSON only, no markdown.
"""

    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    data = json.loads(text)
    candidates = [Candidate(**item) for item in data]
    tokens = response.usage_metadata.total_token_count if hasattr(response, "usage_metadata") else 0

    return ScoutResult(candidates=candidates, searches_used=2, tokens=tokens)
