import os
import time
import asyncio
from datetime import datetime, timedelta
from typing import Literal, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types, errors

from state import TripState
from tools.routing import travel_time
from config import GEMINI_MODEL, MAX_ROUTE_CALLS


FALLBACK_MODEL = "gemini-3.1-flash-lite"


async def _generate_with_retry(client, **kwargs):
    """
    Try primary model first. On 503:
      - attempt 1: retry primary after 1s
      - attempt 2: switch to FALLBACK_MODEL
      - attempt 3: retry fallback after 4s
    Raises on all other errors immediately.
    """
    for attempt in range(4):
        if attempt == 2:
            kwargs = {**kwargs, "model": FALLBACK_MODEL}
        try:
            return await client.aio.models.generate_content(**kwargs)
        except errors.ServerError:
            if attempt == 3:
                raise
            await asyncio.sleep(2 ** (attempt % 2))


# ── Output schema ─────────────────────────────────────────────────────────────

class Stop(BaseModel):
    name: str
    type: Literal["coffee", "food", "outdoor_activity", "park", "market"]
    neighborhood: str
    start_time: str               # format: "9:00 AM"
    end_time: str                 # format: "9:35 AM"
    dwell_minutes: int
    travel_to_next_minutes: int   # 0 for last stop
    travel_mode: str              # "walk", "drive", or "none" for last stop
    est_cost: float
    cost_verified: bool
    lat: float
    lng: float
    reason: str                   # why this stop fits the vibe
    snippets: list[str]
    image_url: Optional[str]


class StopList(BaseModel):
    stops: list[Stop]
    total_cost: float


# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a day trip scheduler. Pick the best 4-5 stops from the \
candidates and build a realistic timed itinerary.

TOOL YOU HAVE:
  get_travel_time(lat1, lng1, lat2, lng2, departure_time)
  - Returns real traffic-aware travel time in minutes and mode (walk/drive)
  - departure_time must be ISO 8601: "YYYY-MM-DDTHH:MM:SS"
  - Call this for every leg: start → stop1, stop1 → stop2, etc.

DWELL TIMES (use these exactly):
  coffee → 35 min · food → 50 min · park → 100 min · outdoor_activity → 100 min · market → 35 min

SCHEDULING:
  Each candidate has snippets from real search results — check them first for
  opening hours, best time to visit, or crowd warnings before scheduling.
  If snippets don't mention hours, use your judgment for that place type.
  Consider the vibe and any explicit time instructions from the user.

BUDGET:
  Total est_cost must not exceed the budget. Prefer cost_verified=true prices."""


def _get_trip_date(date_str: str) -> str:
    """Convert day name or date string to YYYY-MM-DD for HERE API departure_time."""
    day_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    lower = date_str.lower()
    for name, weekday in day_map.items():
        if name in lower:
            today = datetime.now()
            days_ahead = weekday - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    for fmt in ["%Y-%m-%d", "%B %d, %Y", "%B %d", "%b %d"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Fallback: next Saturday
    today = datetime.now()
    days_ahead = 5 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


def _build_user_prompt(state: TripState) -> str:
    trip_date = _get_trip_date(state["date"])
    candidates = state["enriched_candidates"]

    lines = []
    for i, c in enumerate(candidates, 1):
        lat = f"{c['lat']:.4f}" if c["lat"] else "unknown"
        lng = f"{c['lng']:.4f}" if c["lng"] else "unknown"
        dist = f"{c['dist_from_origin_miles']} mi" if c.get("dist_from_origin_miles") is not None else "unknown"
        verified = "verified" if c.get("cost_verified") else "estimated"
        snippets = c.get("snippets", [])
        snippet_text = (" | notes: " + " · ".join(snippets)) if snippets else ""
        lines.append(
            f"{i}. {c['name']} ({c['type']}, {c['neighborhood']}) "
            f"| ${c['est_cost']} {verified} | {dist} from origin "
            f"| coords: {lat},{lng}{snippet_text}"
        )

    candidates_text = "\n".join(lines)

    start_info = ""
    if state.get("start_location") and state.get("start_coords"):
        sc = state["start_coords"]
        start_info = f"\nStarting from: {state['start_location']} ({sc['lat']:.4f},{sc['lng']:.4f})"

    return f"""Plan a day trip with the following details:

City:   {state["city"]}
Date:   {state["date"]} ({trip_date})
Budget: ${state["budget"]}{start_info}
Vibe:   {state["vibe"]}

Candidates:
{candidates_text}

Use get_travel_time for each leg. After routing, I will ask for your final structured itinerary."""


def _build_extraction_prompt(trip_date: str) -> str:
    return f"""Now return the final structured itinerary based on the routing you just completed.

Use {trip_date} as the date in all departure_time values.
Format start_time and end_time as 12-hour time only, e.g. "9:00 AM", "11:30 AM", "2:15 PM".
Carry snippets and image_url from the original candidates into each stop."""


# ── Tool definition ───────────────────────────────────────────────────────────

TRAVEL_TIME_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_travel_time",
            description="Get traffic-aware travel time between two locations.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "lat1": {"type": "NUMBER", "description": "Latitude of origin"},
                    "lng1": {"type": "NUMBER", "description": "Longitude of origin"},
                    "lat2": {"type": "NUMBER", "description": "Latitude of destination"},
                    "lng2": {"type": "NUMBER", "description": "Longitude of destination"},
                    "departure_time": {"type": "STRING", "description": "ISO 8601 e.g. 2025-11-22T09:35:00"},
                },
                "required": ["lat1", "lng1", "lat2", "lng2", "departure_time"],
            },
        )
    ]
)


# ── Node ──────────────────────────────────────────────────────────────────────

async def planner_node(state: TripState) -> dict:
    start = time.time()
    client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))
    trip_date = _get_trip_date(state["date"])

    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text=_build_user_prompt(state))]
        )
    ]

    route_count = 0
    tool_calls_log = []
    total_tokens = 0

    # ── Phase 1: agentic routing loop ─────────────────────────────────────────
    while route_count < MAX_ROUTE_CALLS:
        response = await _generate_with_retry(
            client,
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[TRAVEL_TIME_TOOL],
            ),
        )

        if response.usage_metadata:
            total_tokens += response.usage_metadata.total_token_count

        candidate = response.candidates[0]
        function_calls = [
            part.function_call
            for part in candidate.content.parts
            if hasattr(part, "function_call") and part.function_call
        ]

        if not function_calls:
            break  # LLM finished routing

        tool_result_parts = []
        for fc in function_calls:
            if route_count >= MAX_ROUTE_CALLS:
                break
            args = fc.args
            result = await travel_time(
                lat1=args["lat1"], lng1=args["lng1"],
                lat2=args["lat2"], lng2=args["lng2"],
                departure_time=args["departure_time"],
            )
            route_count += 1

            tool_calls_log.append({
                "tool": "get_travel_time",
                "from": f"{args['lat1']:.3f},{args['lng1']:.3f}",
                "to": f"{args['lat2']:.3f},{args['lng2']:.3f}",
                "departure_time": args["departure_time"],
                "result": result,
            })

            tool_result_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response=result,
                    )
                )
            )

        contents.append(candidate.content)
        contents.append(types.Content(role="user", parts=tool_result_parts))

    # ── Phase 2: structured extraction ────────────────────────────────────────
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part(text=_build_extraction_prompt(trip_date))]
        )
    )

    final_response = await _generate_with_retry(
        client,
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=StopList,
        ),
    )

    if final_response.usage_metadata:
        total_tokens += final_response.usage_metadata.total_token_count

    parsed: StopList = final_response.parsed
    stops = [s.model_dump() for s in parsed.stops]

    # Copy source_videos from enriched candidates by name matching
    candidate_map = {c["name"].lower(): c for c in state.get("enriched_candidates", [])}
    for stop in stops:
        name_lower = stop["name"].lower()
        candidate = candidate_map.get(name_lower)
        if not candidate:
            for cname, c in candidate_map.items():
                if name_lower in cname or cname in name_lower:
                    candidate = c
                    break
        stop["source_videos"] = candidate.get("source_videos", []) if candidate else []
        stop["source_urls"] = candidate.get("source_urls", []) if candidate else []

    latency_ms = int((time.time() - start) * 1000)

    return {
        "stops": stops,
        "trajectory": [{
            "node": "planner",
            "stops_selected": len(stops),
            "total_cost": parsed.total_cost,
            "route_calls": route_count,
            "tool_calls": tool_calls_log,
            "tokens": total_tokens,
            "latency_ms": latency_ms,
        }],
    }
