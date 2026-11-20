import os
import httpx


async def langsearch(query: str, max_results: int = 5) -> dict:
    """
    Run a LangSearch web search and return results.
    Returns:
      {
        "results": [{"title", "content", "url"}, ...],
        "images":  []   # LangSearch doesn't return images
      }
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.langsearch.com/v1/web-search",
            headers={
                "Authorization": f"Bearer {os.getenv('LANGSEARCH_API_KEY')}",
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "count": max_results,
                "contents": {"text": True},
            },
            timeout=15,
        )
        if response.status_code >= 500:
            return {"results": [], "images": []}
        response.raise_for_status()
        data = response.json()

    pages = data.get("data", {}).get("webPages", {}).get("value", [])
    results = [
        {
            "title": p["name"],
            "content": p.get("text", "")[:400],
            "url": p["url"],
        }
        for p in pages
    ]
    return {"results": results, "images": []}
