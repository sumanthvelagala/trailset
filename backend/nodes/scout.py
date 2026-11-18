import os
import time
import json
from google import genai
from google.genai import types

from state import TripState
from tools.search import tavily_search

MAX_TAVILY_SEARCHES = 4

SEARCH_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_places",
            description="Search the web for local places, coffee shops, restaurants, parks, and activities in a city. Use specific queries.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "Search query. Include city name and be specific about place type and vibe.",
                    }
                },
                "required": ["query"],
            },
        )
    ]
)


async def scout_node(state: TripState) -> dict:
    start = time.time()
    client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))

    prompt = f"""You are a local travel scout finding places for a day trip.

City: {state["city"]}
Date: {state["date"]}
Budget: ${state["budget"]} total for the day
Vibe: {state["vibe"]}

Use the search_places tool to find great local spots that match the vibe.
Make 2-4 targeted searches — search for food/coffee AND activities separately.
Avoid tourist traps, chain restaurants, and generic spots.

After searching, return ONLY a JSON array of 8-10 candidate places:
[
  {{
    "name": "place name",
    "type": "coffee|food|outdoor_activity|park|market",
    "neighborhood": "area of city",
    "est_cost": 12.0,
    "description": "one sentence why it fits the vibe"
  }}
]

Return JSON only. No markdown, no explanation."""

    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    search_count = 0
    tool_calls_log = []
    total_tokens = 0

    # Agentic loop — LLM decides what to search and when to stop
    while search_count < MAX_TAVILY_SEARCHES:
        response = await client.aio.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(tools=[SEARCH_TOOL]),
        )

        if response.usage_metadata:
            total_tokens += response.usage_metadata.total_token_count

        candidate = response.candidates[0]
        function_calls = [
            part.function_call
            for part in candidate.content.parts
            if hasattr(part, "function_call") and part.function_call
        ]

        # No tool calls — LLM is done, extract final JSON
        if not function_calls:
            final_text = "".join(
                part.text
                for part in candidate.content.parts
                if hasattr(part, "text") and part.text
            )
            break

        # Execute each tool call
        tool_result_parts = []
        for fc in function_calls:
            if search_count >= MAX_TAVILY_SEARCHES:
                break
            query = fc.args.get("query", "")
            results = await tavily_search(query)
            search_count += 1

            tool_calls_log.append({
                "tool": "search_places",
                "query": query,
                "results_count": len(results),
            })

            tool_result_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"results": results},
                    )
                )
            )

        # Feed tool results back into the conversation
        contents.append(candidate.content)
        contents.append(types.Content(role="user", parts=tool_result_parts))

    # Parse candidates from final LLM response
    text = final_text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    candidates = json.loads(text.strip())

    latency_ms = int((time.time() - start) * 1000)

    return {
        "candidates": candidates,
        "trajectory": [{
            "node": "scout",
            "tool_calls": tool_calls_log,
            "searches_used": search_count,
            "candidates_returned": len(candidates),
            "tokens": total_tokens,
            "latency_ms": latency_ms,
        }],
    }
