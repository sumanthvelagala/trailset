import os
import json
import google.generativeai as genai
from models import Stop, TripRequest


async def run_llm_evals(request: TripRequest, stops: list[Stop]) -> dict:
    genai.configure(api_key=os.getenv("GOOGLE_AI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-flash")

    stops_summary = "\n".join(
        f"- {s.name} ({s.type}): {s.vibe_reason}" for s in stops
    )

    prompt = f"""
You are evaluating a day-trip itinerary. Score each criterion from 1.0 to 5.0.

User vibe: "{request.vibe}"

Itinerary stops:
{stops_summary}

Score these two criteria:
1. vibe_match: Does the itinerary genuinely match the user's vibe? (1=not at all, 5=perfect match)
2. relevance: Are these places actually local and non-touristy (not generic chains or obvious tourist traps)? (1=very generic, 5=very local/authentic)

Return JSON only:
{{"vibe_match": 4.0, "relevance": 3.5}}
"""

    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    return json.loads(text)
