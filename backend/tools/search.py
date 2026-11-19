import os
from tavily import AsyncTavilyClient


async def tavily_search(query: str, max_results: int = 5) -> dict:
    """
    Run a Tavily search and return results + images.
    Returns:
      {
        "results": [{"title", "content", "url"}, ...],
        "images":  ["https://...", ...]   # may be empty
      }
    """
    client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    response = await client.search(
        query,
        max_results=max_results,
        search_depth="basic",
        include_images=True,
    )
    results = [
        {
            "title": r["title"],
            "content": r["content"][:400],
            "url": r["url"],
        }
        for r in response.get("results", [])
    ]
    images = response.get("images", [])
    return {"results": results, "images": images}
