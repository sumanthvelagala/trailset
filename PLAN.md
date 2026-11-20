# Trailset — Project Plan

> AI-powered single-day trip concierge. Enter a city, date, budget, and vibe — get a realistic, timed itinerary with a map.

---

## Product

**Input:** City · Date · Budget (slider $20-$200) · Vibe (tag chips + optional free text) · Starting location (optional)
**Output:** Timed itinerary cards + map with pins + budget bar + dev panel

**Example:**
```
City:    Austin
Date:    Saturday, Nov 22
Budget:  $100
Vibe:    [outdoors] [coffee] [local eats]
         "no tourist traps, dog friendly"   ← optional, max 100 chars
```

**What gets sent to agents:**
```python
vibe = "outdoors, coffee, local eats. no tourist traps, dog friendly"
# tags first, free text appended after period
```

---

## Agent Architecture (LangGraph)

Graph flow:
```
START → scout_node → enrich_node → planner_node → eval_node → END
```

Shared state passed through the graph:
```python
TripState = {
  "city", "date", "budget", "vibe",   # input
  "start_location",                     # optional — e.g. "downtown Austin hotel"
  "start_coords",                       # geocoded from start_location
  "candidates",                         # scout output (8-10 candidates with est_cost + cost_verified)
  "enriched_candidates",                # enrich output (candidates + lat/lng)
  "stops",                              # planner output (final 4-5 stops with schedule)
  "eval_scores",                        # eval output
  "trajectory",                         # each node's log
}
```

### scout_node — Agentic (tool calling)
- Model: `gemini-3.5-flash-lite`
- System prompt: defines role, tool descriptions, query format rules, grounding rules
- Gemini has TWO tools:
  - `search_places(query)` → Tavily web search (blogs, review sites, local guides)
  - `youtube_search(query)` → YouTube top 3 videos + transcripts (first 2,500 chars each)
- LLM decides which tool to call, in what order, up to MAX_TAVILY_SEARCHES=4 + MAX_YOUTUBE_SEARCHES=2
- Query format:
  - web: "[city] [place type] [vibe keywords] [local/hidden/authentic]"
  - youtube: "[city] [vibe] local guide hidden gems [year]"
- 2-phase output:
  - Phase 1: agentic tool calling loop — LLM uses both tools freely, decides when done
  - Phase 2: grounded extraction — all web + YouTube results bundled, LLM extracts candidates
    using ONLY places from those results (prevents hallucination)
- Structured output via `response_schema=CandidateList` (Pydantic, no manual JSON parsing)
- Returns 8-10 candidates intentionally exceeding budget — pool for planner to pick from
- Each candidate: name, type, neighborhood, est_cost, cost_verified, snippets, image_url, source_videos
- source_videos: deterministic string match — candidate name words checked against each transcript
  → if 2+ significant words (>3 chars) found in transcript → video linked to that candidate
  → shown on stop card as YouTube source links
- Logs to trajectory: queries used, results per query, raw_search_results, candidates returned, latency, tokens

### enrich_node — Geocoding (Nominatim)
- No LLM calls — pure deterministic pre-processing step
- Geocodes all 8-10 scout candidates concurrently via Nominatim (OpenStreetMap, free, no key)
- Also geocodes `start_location` if the user provided one
- Adds `lat`, `lng` to each candidate so planner can reason about geography before routing
- Planner needs coordinates upfront to pick geographically sensible stops before calling HERE
- Note: Google Search grounding (hours/prices) dropped — requires paid Gemini plan
- Prices come from scout's LLM estimation with `cost_verified` flag

### planner_node — Agentic (tool calling)
- Model: `gemini-3.5-flash-lite`
- Receives enriched candidates: lat/lng + est_cost + cost_verified already attached
- If start_coords provided, routes from user's starting location to first stop
- Gemini uses one tool:
  - `travel_time(lat1, lng1, lat2, lng2, departure_time, mode)` → minutes (HERE API)
- Transport mode auto-selected by distance:
  - < 0.5 miles → walking (HERE pedestrian mode)
  - >= 0.5 miles → driving (HERE car mode)
- departure_time passed so HERE returns traffic-aware estimates for that day/time
- LLM picks 4-5 open stops, calculates travel legs between them, assigns start times
- Validates: total cost <= budget, schedule fits 9am-7pm window
- Assigns dwell times by place type:
  - Coffee → 35 min · Food → 50 min · Park/outdoor → 100 min · Market → 35 min
- Logs to trajectory: stops selected, budget used, travel legs, latency, tokens

### eval_node
- Runs rule-based + LLM-as-judge evals on final stops
- Logs scores to state

---

## Evals

### Rule-Based (deterministic)
| Eval | Check |
|---|---|
| Budget adherence | sum(costs) <= user budget |
| City correctness | all addresses contain city name |
| Schedule feasibility | no overlapping slots, travel gaps >= 20 min |
| Stop count | 3 <= stops <= 6 |
| Scout coverage | scout returned >= 6 candidates |

### LLM-as-Judge (Gemini 3.5 Flash Lite)
| Eval | Scores |
|---|---|
| Vibe match | 1-5: does itinerary match the user's vibe? |
| Relevance | 1-5: are places local and non-touristy? |

### Trajectory Evaluation (interview-grade)
Each node logs:
- Input state snapshot
- Output produced
- Latency (ms)
- Tokens used
- Tool calls made (which tool, args, result)
- Any failures or retries

### Golden Test Set (regression)
3 fixed inputs run on every deploy:
```
"Austin, Saturday, $100, outdoors + coffee"
"NYC, Sunday, $60, art + brunch, no chains"
"Chicago, Saturday, $80, waterfront + local food"
```

### Tool Failure Handling
- Tavily timeout → retry once, then return partial candidates with warning
- Nominatim fail → stop added without lat/lng, excluded from map only
- HERE fail → fall back to Haversine estimate, flag in observability
- Gemini fail → surface error to user with retry option

---

## Per-Request API Caps

Hard limits enforced in code per trip generation:
```python
MAX_TAVILY_SEARCHES  = 4   # scout web search tool calls
MAX_YOUTUBE_SEARCHES = 2   # scout youtube search tool calls (3 videos + transcripts each)
MAX_GEMINI_CALLS    = 4   # scout parse + planner + eval + llm judge
MAX_GEOCODE_CALLS   = 6   # planner tool calls
MAX_ROUTE_CALLS     = 5   # planner tool calls
```

If cap hit → graceful degrade (Haversine fallback for routing, skip extra searches).

---

## IP Rate Limiting

Prevents one user burning all free tier credits.
Using `slowapi` + Upstash Redis (persists across Render restarts):

```python
5  requests / hour   per IP
20 requests / day    per IP
```

---

## Observability (per request)

```json
{
  "scout_latency_ms": 3200,
  "planner_latency_ms": 2100,
  "eval_latency_ms": 800,
  "total_latency_ms": 6100,
  "tavily_searches": 3,
  "total_tokens": 2460,
  "estimated_cost_usd": 0.0002,
  "trajectory": [
    {
      "node": "scout",
      "tool_calls": [
        {"tool": "search", "query": "Austin local coffee shops South Congress", "results": 5},
        {"tool": "search", "query": "Austin outdoor hidden gems locals love", "results": 5},
        {"tool": "search", "query": "Austin swimming parks not touristy", "results": 4}
      ],
      "candidates_returned": 9,
      "tokens": 1200,
      "latency_ms": 3200
    },
    {
      "node": "planner",
      "tool_calls": [
        {"tool": "geocode", "place": "Bennu Coffee", "result": "30.26, -97.74"},
        {"tool": "travel_time", "mode": "walk", "minutes": 8}
      ],
      "stops_selected": 5,
      "budget_used": 67,
      "tokens": 1260,
      "latency_ms": 2100
    },
    {"node": "eval", "latency_ms": 800}
  ],
  "eval_scores": {
    "budget_ok": true,
    "city_ok": true,
    "schedule_ok": true,
    "stop_count_ok": true,
    "scout_coverage_ok": true,
    "vibe_match": 4.0,
    "relevance": 4.5
  }
}
```

---

## Tech Stack

| Layer | Tool | Free? |
|---|---|---|
| Frontend | Next.js → Vercel | Yes |
| UI components | shadcn/ui + Tailwind | Yes |
| Backend | FastAPI → Render.com | Yes (sleeps after 15 min) |
| Agent orchestration | LangGraph | Yes |
| AI (scout/planner/eval) | Gemini 3.5 Flash Lite (Google AI Studio) | Yes (1500 req/day) |
| AI (enrichment) | Gemini 2.5 Flash + Google Search grounding | Yes (500 grounding req/day) |
| Web Search | Tavily | Yes (1000 searches/mo) |
| Routing | HERE Routing API | Yes (30,000/mo, no credit card) |
| Geocoding | Nominatim (OpenStreetMap) | Yes, no key |
| Map rendering | Leaflet.js | Yes |
| Rate limiting | slowapi + Upstash Redis | Yes (10k commands/day) |
| Render keep-alive | cron-job.org ping /health every 10 min | Yes |

---

## UI Design

### Input Page (/)
- City text input
- Date picker
- Budget slider ($20 - $200)
- Vibe tag chips: [outdoors] [coffee] [local eats] [art] [nightlife] [family-friendly]
  - At least 1 tag required
- Free text input (optional, max 100 chars)
  - Placeholder: "e.g. no tourist traps, dog friendly, prefer walking"
  - Live character counter (turns red at 10 remaining)
- Starting location input (optional)
  - Placeholder: "e.g. downtown Austin hotel, Austin airport"
  - Used to route from user's location to first stop
- Generate button with loading state

### Results Page (/results)
```
┌─────────────────────┬──────────────────┐
│  Stop cards         │   Leaflet map    │
│  (numbered, timed)  │   (pins + route) │
│                     │                  │
├─────────────────────┴──────────────────┤
│  Budget bar  ████████░░░  $67 / $100   │
├────────────────────────────────────────┤
│  [Dev panel — collapsed by default]    │
│  Latency · Tokens · Cost · Evals       │
│  Trajectory per node + tool calls      │
└────────────────────────────────────────┘
```

Each stop card: name, time slot, dwell time, travel to next (walk/drive + minutes), estimated cost, vibe reason, "Verify hours before visiting" disclaimer

---

## Out of Scope (V1)

- Opening hours verification → NOW IN SCOPE via enrich_node (gemini-2.5-flash + Google Search)
- User accounts / saved trips
- Booking links
- Mobile app
- Multi-day trips
- Chat interface (V2: "refine my itinerary" after generation)

---

## Project Structure

```
trailset/
├── frontend/
│   ├── app/
│   │   ├── page.tsx              # Input form
│   │   └── results/page.tsx      # Itinerary + map
│   └── components/
│       ├── TripForm.tsx           # City, date, budget slider, vibe chips
│       ├── ItineraryCard.tsx      # Single stop card
│       ├── MapView.tsx            # Leaflet map with pins
│       ├── BudgetBar.tsx          # Visual budget progress
│       └── DevPanel.tsx           # Evals + trajectory + observability
├── backend/
│   ├── main.py                    # FastAPI + /health + /plan + rate limiting
│   ├── state.py                   # TripState TypedDict
│   ├── graph.py                   # LangGraph StateGraph definition
│   ├── nodes/
│   │   ├── scout.py               # scout_node (Tavily tool calling)
│   │   ├── planner.py             # planner_node (geocode + HERE tools)
│   │   └── eval.py                # eval_node (rule-based + llm-judge)
│   ├── tools/
│   │   ├── search.py              # Tavily search tool
│   │   ├── geocode.py             # Nominatim tool
│   │   └── routing.py             # HERE routing tool (walk/drive)
│   ├── evals/
│   │   ├── rule_based.py          # Deterministic checks
│   │   └── llm_judge.py           # LLM-as-judge scoring
│   ├── models.py                  # Pydantic schemas
│   └── requirements.txt
├── tests/
│   └── golden_set.py              # Regression test suite
├── PLAN.md
├── README.md
├── .env.example
└── .gitignore
```

---

## 10-Day Build Plan

```
Day 1   Setup: scaffold, API keys, /health live                              [DONE]
Day 2   LangGraph: state.py, graph.py, scout_node with Tavily tool calling   [DONE]
Day 3   enrich_node: geocode (Nominatim) + gemini-2.5-flash Google Search (hours + real prices)
Day 4   planner_node: HERE routing tool (traffic-aware travel times + schedule building)
Day 5   eval_node: rule-based + LLM-as-judge + trajectory + golden test set
Day 6   Next.js UI: input form with shadcn/ui (slider, chips, date picker)
Day 7   Results page: itinerary cards + budget bar
Day 8   Map view: Leaflet + pins + walk/drive indicators
Day 9   Deploy: Vercel + Render + Upstash rate limiting + cron ping
Day 10  Dev panel, edge case testing, polish, README
```

---

## API Keys Needed

- `GOOGLE_AI_API_KEY` — Gemini 3.5 Flash Lite + Gemini 2.5 Flash (same key) [DONE]
- `TAVILY_API_KEY` — Tavily search [DONE]
- `HERE_API_KEY` — HERE Routing API (developer.here.com, free, no credit card)
- `UPSTASH_REDIS_URL` — Rate limiting (upstash.com, free tier) — add on Day 9
- Nominatim — no key needed

---

## Key Interview Talking Points

- LangGraph over custom agents: shared state, built-in observability, retries, industry standard
- Truly agentic tool calling: LLM decides what to search and how many times (Scout)
- Real routing with departure-time traffic awareness (HERE API)
- Trajectory evaluation: per-node tool call logging, not just final output
- LLM-as-judge for subjective quality scoring
- Golden test sets for regression detection
- Graceful degradation: HERE fails → Haversine fallback
- IP rate limiting to protect free tier credits
- Per-request API caps to prevent runaway costs
- When NOT to use agents (justify the complexity)
