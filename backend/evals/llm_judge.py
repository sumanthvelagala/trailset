import os
import asyncio
from pydantic import BaseModel
from google import genai
from google.genai import types, errors

from config import GEMINI_MODEL

FALLBACK_MODEL = "gemini-3.1-flash-lite"


class JudgeScores(BaseModel):
    vibe_match: float       # 1-5: does itinerary match the user's vibe?
    relevance: float        # 1-5: are places local and non-touristy?
    reasoning: str          # one sentence explaining the scores


async def _generate_with_retry(client, **kwargs):
    for attempt in range(4):
        if attempt == 2:
            kwargs = {**kwargs, "model": FALLBACK_MODEL}
        try:
            return await client.aio.models.generate_content(**kwargs)
        except errors.ServerError:
            if attempt == 3:
                raise
            await asyncio.sleep(2 ** (attempt % 2))


async def run_llm_evals(state: dict) -> dict:
    stops = state.get("stops", [])
    vibe = state.get("vibe", "")

    stops_summary = "\n".join(
        f"- {s['name']} ({s['type']}, {s.get('neighborhood', '')}): {s.get('reason', '')}"
        for s in stops
    )

    prompt = f"""Evaluate this day-trip itinerary.

User vibe: "{vibe}"

Itinerary:
{stops_summary}

Score vibe_match (1-5): does the itinerary genuinely match the user's vibe?
Score relevance (1-5): are these places actually local and non-touristy (not chains or obvious tourist traps)?
Add one sentence of reasoning.
"""

    client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))
    response = await _generate_with_retry(
        client,
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JudgeScores,
        ),
    )

    parsed: JudgeScores = response.parsed
    return {
        "vibe_match": parsed.vibe_match,
        "relevance": parsed.relevance,
        "reasoning": parsed.reasoning,
    }
