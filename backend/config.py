GEMINI_MODEL            = "gemini-3.5-flash-lite"   # scout, planner, eval (primary)
GEMINI_FALLBACK_MODEL   = "gemini-3.1-flash-lite"   # fallback on 503
GEMINI_GROUNDING_MODEL  = "gemini-2.5-flash"        # enrich node (Google Search built-in)

MAX_LANGSEARCH_SEARCHES = 2
MAX_YOUTUBE_SEARCHES = 2
MAX_GEMINI_CALLS     = 4
MAX_GEOCODE_CALLS    = 6
MAX_ROUTE_CALLS      = 5
MAX_SCOUT_RETRIES    = 2
MAX_PLANNER_RETRIES  = 2

DAILY_HERE_LIMIT      = 500   # self-imposed daily cap (free tier is 30k/month = ~1000/day)
# DAILY_GROUNDING_LIMIT removed — Google Search grounding not available on free tier
