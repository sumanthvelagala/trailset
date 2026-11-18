import os
from tavily import AsyncTavilyClient


async def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """Run a Tavily search and return cleaned results."""
    client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    result = await client.search(query, max_results=max_results, search_depth="basic")
    return [
        {
            "title": r["title"],
            "content": r["content"][:300],
            "url": r["url"],
        }
        for r in result.get("results", [])
    ]
