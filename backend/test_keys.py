"""Quick script to verify all API keys and dependencies work."""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv("../.env")


def test_gemini():
    from google import genai
    client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents="Say 'Gemini OK' and nothing else.",
    )
    print(f"  Gemini:    {response.text.strip()}")


def test_tavily():
    from tavily import TavilyClient
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    result = client.search("best coffee shops Austin TX", max_results=1)
    title = result["results"][0]["title"] if result["results"] else "no results"
    print(f"  Tavily:    OK — first result: '{title}'")


async def test_nominatim():
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": "Barton Springs Pool, Austin", "format": "json", "limit": 1},
            headers={"User-Agent": "trailset-test/1.0"},
            timeout=10,
        )
        data = resp.json()
        if data:
            print(f"  Nominatim: OK — lat={data[0]['lat']}, lon={data[0]['lon']}")
        else:
            print("  Nominatim: no results")


if __name__ == "__main__":
    print("\nTesting API keys...\n")

    print("[1] Gemini 3.5 Flash Lite")
    try:
        test_gemini()
    except Exception as e:
        print(f"  Gemini:    FAILED — {e}")

    print("\n[2] Tavily Search")
    try:
        test_tavily()
    except Exception as e:
        print(f"  Tavily:    FAILED — {e}")

    print("\n[3] Nominatim (no key needed)")
    try:
        asyncio.run(test_nominatim())
    except Exception as e:
        print(f"  Nominatim: FAILED — {e}")

    print("\nDone.\n")
