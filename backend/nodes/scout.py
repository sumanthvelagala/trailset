import os
import time
import asyncio
from typing import Literal, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types, errors

from state import TripState
from tools.search import langsearch
from tools.youtube import youtube_search, _match_sources
from config import GEMINI_MODEL, MAX_LANGSEARCH_SEARCHES, MAX_YOUTUBE_SEARCHES

FALLBACK_MODEL = "gemini-3.1-flash-lite"


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


# ── Schemas ───────────────────────────────────────────────────────────────────

class SearchPlan(BaseModel):
    langsearch_queries: list[str]   # 2 web search queries
    youtube_queries: list[str]      # 1-2 YouTube queries


class Candidate(BaseModel):
    name: str
    type: Literal["coffee", "food", "outdoor_activity", "park", "market"]
    neighborhood: str
    est_cost: float
    cost_verified: bool
    description: str
    snippets: list[str]
    image_url: Optional[str]


class CandidateList(BaseModel):
    candidates: list[Candidate]


# ── Tool ──────────────────────────────────────────────────────────────────────

SEARCH_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_places",
            description="Search the web for local places, restaurants, parks, and activities.",
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


# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the best day trip planner. \
You find places based on exactly what the user is looking for — their city, budget, vibe, and date. \
You ONLY recommend places from your search results — never from your own knowledge. \
Every place must have come from a web or YouTube source you searched."""


QUERY_RULES = """HOW TO WRITE GOOD QUERIES:
  search_places(query) — searches the web, returns results from travel blogs, local guides, review sites
  youtube_search(query) — searches YouTube, returns content from local travel and food videos

  Rules:
  - Always include the city name
  - Target a specific neighborhood or area, not just the city center
  - Use what locals search for, not tourist language
  - Add qualifiers like "locals love", "neighborhood", "worth it", "best kept secret"
  - For food: include price range like "under $15" or "affordable" if budget is tight
  - For activities: include "free" or "cheap" if budget is tight
  - Reddit-style phrasing works well: "{city} [place type] reddit" or "{city} [neighborhood] [place type] worth it"

  Good search_places:   "{city} [neighborhood] coffee shop locals go not tourists"
                        "{city} affordable brunch spots locals recommend under $15"
                        "{city} free outdoor parks hiking trails worth visiting"
                        "{city} [vibe keyword] best kept secret spots reddit"

  Good youtube_search:  "{city} honest local food guide 2025"
                        "{city} [vibe] spots locals actually go to"

  Bad queries: "things to do in {city}" / "{city} coffee" / "best restaurants {city}"
               — too generic, returns tourist traps"""


PLAN_PROMPT = """A user wants a day trip. Find them the best spots that match what they asked for.

City:   {city}
Date:   {date}
Budget: ${budget} total for the entire day
Vibe:   {vibe}

{query_rules}

You get exactly:
- 2 search_places queries: target specific place types from the vibe (coffee, food, parks, activities)
- 1-2 youtube_search queries: broad city vibe guides or hidden gems videos

Make every query count — 2 web + 1-2 YouTube is all you get for the initial search."""


def _build_results_text(all_results: list[dict]) -> str:
    text = ""
    for entry in all_results:
        text += f"\n--- Source: \"{entry['query']}\" ---\n"
        for r in entry["results"]:
            text += f"  - {r['title']}: {r['content']}\n"
    return text


FOLLOWUP_EXTRACT_PROMPT = """Here are the results from your searches:
{results_text}

STEP 1 — Fill gaps if needed (optional):
Look at what you searched and what came back. \
If you are missing place types the user asked for in "{vibe}", \
use search_places up to 3 more times to fill those gaps. \
Skip this step if you already have good variety.

{query_rules}

STEP 2 — Return candidates:
Return 8-10 places using ONLY what appeared in your search results.

For each candidate:
- description: one sentence why it matches what the user asked for
- neighborhood: copy the exact neighborhood/area stated in the source text. \
  If the source only says the city, write the city name. NEVER guess or infer a neighborhood \
  that isn't explicitly in the source — wrong neighborhoods break routing.
- snippets: 2-3 specific details from results — opening hours, prices, what to order, tips. \
  At least one snippet should include the address or confirm the neighborhood.
- image_url: best matching image from available images below, or null
- est_cost: price per person. Mentioned in results → extract it, cost_verified=true. \
  Not mentioned → estimate by place type, cost_verified=false.
- Individual cost under ${budget_half:.0f} so total day fits within ${budget}
- Include a mix of food/drinks AND activities/parks
- Skip any place if its source text does not confirm it is in {city}

Available images:
{images_text}

NEVER recommend a place that did not appear in your search results."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _match_web_sources(place_name: str, results: list[dict]) -> list[dict]:
    """
    Match a place name against web result titles/content.
    Returns up to 2 matching {title, url} dicts.
    Same 2-significant-word logic as _match_sources for YouTube.
    """
    name_words = [w.lower() for w in place_name.split() if len(w) > 3]
    if not name_words:
        return []
    threshold = min(2, len(name_words))
    matched = []
    seen_urls = set()
    for r in results:
        if r["url"] in seen_urls:
            continue
        searchable = (r.get("title", "") + " " + r.get("content", "")).lower()
        hits = sum(1 for w in name_words if w in searchable)
        if hits >= threshold:
            matched.append({"title": r["title"], "url": r["url"]})
            seen_urls.add(r["url"])
        if len(matched) >= 2:
            break
    return matched


# ── Node ──────────────────────────────────────────────────────────────────────

async def scout_node(state: TripState) -> dict:
    start = time.time()
    client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))
    total_tokens = 0
    tool_calls_log = []
    all_results = []
    all_youtube_videos = []

    # ── Phase 0: LLM plans initial queries ────────────────────────────────────
    plan_prompt = PLAN_PROMPT.format(
        city=state["city"],
        date=state["date"],
        budget=state["budget"],
        vibe=state["vibe"],
        query_rules=QUERY_RULES,
    )
    if state.get("retry_feedback"):
        plan_prompt += f"\n\nNOTE — previous attempt failed: {state['retry_feedback']}\nPlease fix this."

    plan_response = await _generate_with_retry(
        client,
        model=GEMINI_MODEL,
        contents=[types.Content(role="user", parts=[types.Part(text=plan_prompt)])],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=SearchPlan,
        ),
    )
    if plan_response.usage_metadata:
        total_tokens += plan_response.usage_metadata.total_token_count

    plan: SearchPlan = plan_response.parsed
    ls_queries = plan.langsearch_queries[:MAX_LANGSEARCH_SEARCHES]
    yt_queries = plan.youtube_queries[:MAX_YOUTUBE_SEARCHES]

    # ── Phase 1: Parallel fetch initial queries ────────────────────────────────
    fetched = await asyncio.gather(
        *[langsearch(q) for q in ls_queries],
        *[youtube_search(q) for q in yt_queries],
        return_exceptions=True,
    )

    ls_fetched = fetched[:len(ls_queries)]
    yt_fetched = fetched[len(ls_queries):]

    for query, result in zip(ls_queries, ls_fetched):
        if isinstance(result, Exception):
            continue
        tool_calls_log.append({"tool": "langsearch", "query": query, "results_count": len(result["results"])})
        all_results.append({"query": query, "results": result["results"], "images": result.get("images", [])})

    for query, result in zip(yt_queries, yt_fetched):
        if isinstance(result, Exception):
            continue
        tool_calls_log.append({"tool": "youtube_search", "query": query, "results_count": len(result["results"])})
        all_results.append({"query": f"[YouTube] {query}", "results": result["results"], "images": []})
        all_youtube_videos.extend(result.get("videos", []))

    # ── Phase 2: Agentic follow-up — LLM sees results, can search 3 more ──────
    extra_searches = 0
    max_extra = 3

    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text=FOLLOWUP_EXTRACT_PROMPT.format(
                results_text=_build_results_text(all_results),
                vibe=state["vibe"],
                city=state["city"],
                query_rules=QUERY_RULES,
                budget_half=state["budget"] / 2,
                budget=state["budget"],
                images_text="(images listed after all searches complete)",
            ))]
        )
    ]

    while extra_searches < max_extra:
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

        function_calls = [
            part.function_call
            for part in response.candidates[0].content.parts
            if hasattr(part, "function_call") and part.function_call
        ]

        if not function_calls:
            break  # LLM satisfied with current data

        contents.append(response.candidates[0].content)

        # Clamp to remaining budget
        allowed = function_calls[:max_extra - extra_searches]
        if not allowed:
            break

        # Run all tool calls in this batch in parallel
        queries = [fc.args.get("query", "") for fc in allowed]
        batch_results = await asyncio.gather(*[langsearch(q) for q in queries], return_exceptions=True)

        tool_result_parts = []
        for fc, query, result in zip(allowed, queries, batch_results):
            if isinstance(result, Exception):
                continue
            extra_searches += 1
            tool_calls_log.append({"tool": "langsearch_extra", "query": query, "results_count": len(result["results"])})
            all_results.append({"query": query, "results": result["results"], "images": result.get("images", [])})
            tool_result_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"results": result["results"]},
                    )
                )
            )

        if tool_result_parts:
            contents.append(types.Content(role="user", parts=tool_result_parts))

    # ── Phase 3: Extract candidates from all accumulated results ──────────────
    all_images = [img for entry in all_results for img in entry.get("images", [])]
    images_text = "\n".join(f"  {url}" for url in all_images[:20]) if all_images else "  (none)"

    contents.append(
        types.Content(
            role="user",
            parts=[types.Part(text=f"""Now return the candidates JSON.

For each candidate:
- description: one sentence why it matches the vibe "{state['vibe']}"
- neighborhood: copy the exact neighborhood/area from the source text. \
  Never guess — if the source doesn't name a neighborhood, use "{state['city']}". \
  Wrong neighborhoods break the map routing.
- snippets: 2-3 specific details — opening hours, prices, what to order, tips. \
  Include the address or neighborhood confirmation in at least one snippet.
- image_url: best matching image from available images below, or null
- est_cost: price per person. Mentioned in results → extract it, cost_verified=true. Not mentioned → estimate, cost_verified=false.
- Individual cost under ${state['budget'] / 2:.0f} so total day fits within ${state['budget']}
- Mix of food/drinks AND activities/parks
- Only include places confirmed to be in {state['city']} by their source text

Available images:
{images_text}

NEVER recommend a place that did not appear in your search results.""")]
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

    # ── Post-extraction: deterministic source matching ─────────────────────────
    # Build a flat list of all web results for URL matching
    all_web_results = [r for entry in all_results for r in entry["results"]
                       if not entry["query"].startswith("[YouTube]")]

    for candidate in candidates:
        candidate["source_videos"] = _match_sources(candidate["name"], all_youtube_videos)
        candidate["source_urls"] = _match_web_sources(candidate["name"], all_web_results)

    latency_ms = int((time.time() - start) * 1000)

    return {
        "candidates": candidates,
        "trajectory": [{
            "node": "scout",
            "tool_calls": tool_calls_log,
            "raw_search_results": all_results,
            "searches_used": len(ls_queries) + extra_searches,
            "youtube_searches_used": len(yt_queries),
            "extra_searches_used": extra_searches,
            "candidates_returned": len(candidates),
            "tokens": total_tokens,
            "latency_ms": latency_ms,
        }],
    }
