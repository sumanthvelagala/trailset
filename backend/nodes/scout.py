import os
import time
import asyncio
from typing import Literal, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types, errors

from state import TripState
from tools.search import tavily_search
from config import GEMINI_MODEL, MAX_TAVILY_SEARCHES

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


# ── Structured output schema ──────────────────────────────────────────────────

class Candidate(BaseModel):
    name: str
    type: Literal["coffee", "food", "outdoor_activity", "park", "market"]
    neighborhood: str
    est_cost: float
    cost_verified: bool          # True if price came from search results, False if LLM estimated
    description: str             # one sentence why it fits the vibe
    snippets: list[str]          # 2-3 relevant lines from search results (tips, details, highlights)
    image_url: Optional[str]     # best matching image from search results, or null


class CandidateList(BaseModel):
    candidates: list[Candidate]


# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a local travel scout. Your job is to find authentic, \
non-touristy places for a day trip that match the user's vibe.

TOOL YOU HAVE:
  search_places(query: str)
  - Searches the web and returns real results from travel sites and local blogs
  - Use it 2-4 times with different, specific queries

HOW TO WRITE QUERIES:
  Format: "[city] [specific place type] [vibe keywords] [local/hidden/authentic]"

  Good: "Austin independent coffee shops South Congress locals love"
  Good: "Austin outdoor swimming holes hidden gems not touristy"
  Bad:  "Austin coffee"
  Bad:  "things to do Austin"

  Rules:
  - Always include the city name
  - Split food/coffee and activities into separate searches
  - Use "local", "hidden gem", "independent", "authentic" when vibe avoids tourist traps
  - Use the user's vibe keywords directly in queries

COST ESTIMATION:
  For each place, set est_cost = price per person and cost_verified based on this rule:

  If the search results mention a price (e.g. "$12-15 per person", "entry fee $9"):
    → Extract it (e.g. "$12-15" → 13.50), set cost_verified=true

  If no price is mentioned in the results:
    → Estimate based on the specific place — its type, reputation, and neighborhood.
      Do NOT use generic flat defaults.
      Set cost_verified=false to flag it as an estimate.

IMPORTANT — WHY WE WANT MORE THAN THE BUDGET:
  You are finding a POOL of candidates, not the final itinerary.
  The planner agent will select the best 4-5 stops later based on
  geography, travel time, and budget. So intentionally return 8-10
  candidates whose individual costs are each under half the budget.
  Their total WILL exceed the budget — that is expected and correct.

GROUNDING RULE:
  ONLY recommend places that appeared in your search results.
  Do not invent or hallucinate places. Every candidate must be
  traceable to something in the search results."""


def _build_user_prompt(state: TripState) -> str:
    base = f"""Find places for a day trip:

City:   {state["city"]}
Date:   {state["date"]}
Budget: ${state["budget"]} total for the entire day (find candidates up to 2x this amount)
Vibe:   {state["vibe"]}

Use search_places to find real local spots. After searching I will ask for your final list."""

    if state.get("retry_feedback"):
        base += f"\n\nNOTE — previous attempt failed: {state['retry_feedback']}\nPlease fix this."

    return base


def _build_grounding_prompt(all_results: list[dict], state: TripState) -> str:
    results_text = ""
    all_images = []
    for entry in all_results:
        results_text += f"\n--- Search: \"{entry['query']}\" ---\n"
        for r in entry["results"]:
            results_text += f"  - {r['title']}: {r['content']}\n"
        all_images.extend(entry.get("images", []))

    images_text = "\n".join(f"  {url}" for url in all_images[:20]) if all_images else "  (none)"

    return f"""Here are ALL the search results from your searches:
{results_text}

Available images from search results:
{images_text}

Based ONLY on the results above, return 8-10 candidate places.
Every candidate must have appeared in the search results.
Do not add any place that was not found above.

For each candidate:
- description: one sentence why it fits the vibe "{state["vibe"]}"
- snippets: pick 2-3 specific details from the search results about this place —
  tips, highlights, what to try, best time to visit, dog-friendly notes, etc.
  These should be specific to this place, not generic.
- image_url: pick the most relevant image URL from the available images above
  that best matches this place. Set null if none seem relevant.
- Individual cost of each place should be under ${state["budget"] / 2:.0f}
- Include a mix of food/coffee AND activities/parks
"""


# ── Tool definition ───────────────────────────────────────────────────────────

SEARCH_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_places",
            description="Search the web for local places, coffee shops, restaurants, parks, and activities.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "Search query. Include city + specific place type + vibe keywords.",
                    }
                },
                "required": ["query"],
            },
        )
    ]
)


# ── Node ──────────────────────────────────────────────────────────────────────

async def scout_node(state: TripState) -> dict:
    start = time.time()
    client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))

    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text=_build_user_prompt(state))]
        )
    ]

    search_count = 0
    tool_calls_log = []
    all_results = []   # collect every search result for grounding
    total_tokens = 0

    # ── Phase 1: agentic tool calling loop ────────────────────────────────────
    while search_count < MAX_TAVILY_SEARCHES:
        response = await _generate_with_retry(
            client,
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[SEARCH_TOOL],
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
            break  # LLM decided it has enough data

        tool_result_parts = []
        for fc in function_calls:
            if search_count >= MAX_TAVILY_SEARCHES:
                break
            query = fc.args.get("query", "")
            search_data = await tavily_search(query)
            search_count += 1

            tool_calls_log.append({
                "tool": "search_places",
                "query": query,
                "results_count": len(search_data["results"]),
                "images_count": len(search_data["images"]),
            })
            all_results.append({
                "query": query,
                "results": search_data["results"],
                "images": search_data["images"],
            })

            tool_result_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"results": search_data["results"]},
                    )
                )
            )

        contents.append(candidate.content)
        contents.append(types.Content(role="user", parts=tool_result_parts))

    # ── Phase 2: grounded structured extraction ───────────────────────────────
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part(text=_build_grounding_prompt(all_results, state))]
        )
    )

    final_response = await _generate_with_retry(
        client,
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=CandidateList,
        ),
    )

    if final_response.usage_metadata:
        total_tokens += final_response.usage_metadata.total_token_count

    parsed: CandidateList = final_response.parsed
    candidates = [c.model_dump() for c in parsed.candidates]

    latency_ms = int((time.time() - start) * 1000)

    return {
        "candidates": candidates,
        "trajectory": [{
            "node": "scout",
            "tool_calls": tool_calls_log,
            "raw_search_results": all_results,   # kept for grounding checks
            "searches_used": search_count,
            "candidates_returned": len(candidates),
            "tokens": total_tokens,
            "latency_ms": latency_ms,
        }],
    }
