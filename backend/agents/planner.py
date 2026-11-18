import os
import json
import asyncio
from dataclasses import dataclass
from google import genai

from models import Candidate, Stop
from utils.geocode import geocode
from utils.haversine import travel_time_minutes

DWELL_TIMES = {
    "coffee": 35,
    "food": 50,
    "outdoor_activity": 100,
    "park": 100,
    "market": 35,
}


@dataclass
class PlannerResult:
    stops: list[Stop]
    tokens: int


async def run_planner(request, candidates: list[Candidate]) -> PlannerResult:
    client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))

    candidates_json = json.dumps([c.model_dump() for c in candidates], indent=2)

    prompt = f"""
You are a day-trip planner. Select and order 4-5 stops from the candidates for a realistic day trip.

City: {request.city}
Date: {request.date}
Budget: ${request.budget}
Vibe: {request.vibe}

Candidates:
{candidates_json}

Rules:
- Total est_cost must be under ${request.budget}
- Start around 9:00am, end by 7:00pm
- Mix of food and activities
- Order geographically to minimize backtracking (group by neighborhood)
- Include a vibe_reason for each stop explaining why it fits

Return a JSON array of stops:
{{
  "name": "place name",
  "type": "coffee|food|outdoor_activity|park|market",
  "address": "full address in {request.city}",
  "start_time": "10:00am",
  "dwell_min": 45,
  "est_cost": 12.0,
  "vibe_reason": "why this fits the vibe"
}}

Return JSON only, no markdown.
"""

    response = client.models.generate_content(model="gemini-3.5-flash-lite", contents=prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    data = json.loads(text)
    tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0

    # Geocode all stops in parallel
    coords = await asyncio.gather(*[geocode(s["name"], request.city) for s in data])

    stops = []
    for i, (item, coord) in enumerate(zip(data, coords)):
        lat, lng = coord if coord else (None, None)

        # Calculate travel time to next stop
        travel_min = 0
        if i < len(data) - 1 and coord:
            next_coord = coords[i + 1]
            if next_coord:
                travel_min = travel_time_minutes(lat, lng, next_coord[0], next_coord[1])

        stops.append(Stop(
            name=item["name"],
            type=item["type"],
            address=item["address"],
            lat=lat,
            lng=lng,
            start_time=item["start_time"],
            dwell_min=item.get("dwell_min", DWELL_TIMES.get(item["type"], 45)),
            travel_to_next_min=travel_min,
            est_cost=item["est_cost"],
            vibe_reason=item["vibe_reason"],
        ))

    return PlannerResult(stops=stops, tokens=tokens)
