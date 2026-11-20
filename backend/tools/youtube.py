import os
import asyncio
from googleapiclient.discovery import build

MAX_SEARCH_RESULTS = 7   # videos to fetch from search
MAX_VIDEOS         = 5   # videos to keep after fetching descriptions
DESCRIPTION_CHARS  = 1000  # first N chars of description to pass to LLM


def _search_videos(query: str) -> list[dict]:
    """Search YouTube, return top MAX_SEARCH_RESULTS video metadata."""
    api_key = os.getenv("YOUTUBE_API_KEY")
    youtube = build("youtube", "v3", developerKey=api_key)
    res = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=MAX_SEARCH_RESULTS,
        relevanceLanguage="en",
    ).execute()

    videos = []
    for item in res.get("items", []):
        videos.append({
            "video_id": item["id"]["videoId"],
            "title":    item["snippet"]["title"],
            "channel":  item["snippet"]["channelTitle"],
            "url":      f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            "thumbnail": item["snippet"]["thumbnails"].get("medium", {}).get("url"),
        })
    return videos


def _fetch_descriptions(video_ids: list[str]) -> dict[str, dict]:
    """
    Fetch full description + tags for a batch of video IDs via videos.list.
    Costs 1 quota unit total (not per video). Returns {video_id: {description, tags}}.
    """
    if not video_ids:
        return {}

    api_key = os.getenv("YOUTUBE_API_KEY")
    youtube = build("youtube", "v3", developerKey=api_key)
    res = youtube.videos().list(
        part="snippet",
        id=",".join(video_ids),
    ).execute()

    result = {}
    for item in res.get("items", []):
        vid = item["id"]
        snippet = item.get("snippet", {})
        result[vid] = {
            "description": snippet.get("description", "")[:DESCRIPTION_CHARS],
            "tags": snippet.get("tags", []),
        }
    return result


def _match_sources(place_name: str, videos: list[dict]) -> list[dict]:
    """
    Match a place name against each video's title + description + tags.
    Match if 2+ significant words (>3 chars) from the place name are found.
    Returns list of matched video dicts (without raw description text).
    """
    name_words = [w.lower() for w in place_name.split() if len(w) > 3]
    if not name_words:
        return []

    threshold = min(2, len(name_words))
    matched = []
    for video in videos:
        # Combine title + description + tags into one searchable string
        searchable = " ".join([
            video.get("title", ""),
            video.get("description", ""),
            " ".join(video.get("tags", [])),
        ]).lower()

        hits = sum(1 for w in name_words if w in searchable)
        if hits >= threshold:
            matched.append({
                "title":     video["title"],
                "url":       video["url"],
                "thumbnail": video["thumbnail"],
                "channel":   video["channel"],
            })
    return matched


async def youtube_search(query: str) -> dict:
    """
    Search YouTube, fetch full descriptions + tags via videos.list.
    Returns:
      {
        "results": [{"title", "content", "url"}, ...],  # for LLM context
        "videos":  [{...full metadata with description + tags...}]  # for source matching
      }
    """
    loop = asyncio.get_event_loop()

    # search.list — 100 quota units
    videos = await loop.run_in_executor(None, _search_videos, query)
    if not videos:
        return {"results": [], "videos": []}

    # videos.list — 1 quota unit for the whole batch
    video_ids = [v["video_id"] for v in videos]
    descriptions = await loop.run_in_executor(None, _fetch_descriptions, video_ids)

    # Attach description + tags to each video
    for video in videos:
        info = descriptions.get(video["video_id"], {})
        video["description"] = info.get("description", "")
        video["tags"] = info.get("tags", [])

    # Keep top MAX_VIDEOS, build LLM-friendly results
    videos = videos[:MAX_VIDEOS]
    results = [
        {
            "title":   v["title"],
            "content": f"{v['description']} Tags: {', '.join(v['tags'][:10])}".strip(),
            "url":     v["url"],
        }
        for v in videos
        if v["description"] or v["tags"]
    ]

    return {
        "results": results,   # same shape as LangSearch results — fed to LLM
        "videos":  videos,    # full metadata for _match_sources
    }
