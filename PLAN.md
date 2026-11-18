# Trailset — Project Plan

> AI-powered single-day trip concierge. Enter a city, date, budget, and vibe — get a realistic, timed itinerary with a map.

---

## Product

**Input:** City · Date · Budget (slider $20-$200) · Vibe (tag chips)
**Output:** Timed itinerary cards + map with pins + budget bar + dev panel

**Example:**
```
City:   Austin
Date:   Saturday, Nov 22
Budget: $100
Vibe:   [outdoors] [coffee] [local eats]
```

---

## Agent Architecture (LangGraph)

Graph flow:
```
START → scout_node → planner_node → eval_node → END
```

Shared state passed through the graph:
```python
TripState = {
  "city", "date", "budget", "vibe",   # input
  "candidates",                         # scout output
  "stops",                              # planner output
  "trajectory",                         # each node's log
  "observability"                       # latency, tokens, cost
}
```

### scout_node
- Runs 2 parallel Tavily searches:
  - `"{city} best local coffee brunch lunch not touristy {vibe}"`
  - `"{city} outdoor activities parks hidden gems {day} {vibe}"`
- Gemini 2.5 Flash parses results → 8-10 candidates
- Logs to trajectory: query, raw results, candidates returned, latency, tokens

### planner_node
- Takes candidates from state
- Geocodes each via Nominatim (OSM) → lat/lng
- Assigns dwell time by type:
  - Coffee shop → 35 min
  - Brunch/lunch → 50 min
  - Park/hiking → 100 min
  - Outdoor activity → 100 min
  - Market/browse → 35 min
- Calculates travel time: Haversine distance + speed estimate
  - Walking (<0.3 miles) → 20 min/mile
  - Driving → 20mph city estimate
- Gemini 2.5 Flash picks 4-5 stops, assigns start times, validates budget
- Logs to trajectory: candidates in, stops out, budget used, latency, tokens

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

### LLM-as-Judge (Gemini 2.5 Flash)
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
- Any tool failures or retries

This enables step-level debugging, not just final output checking.

### Golden Test Set (regression)
3-5 fixed inputs with known acceptable outputs. Run on every deploy to catch regressions.
```
"Austin, Saturday, $100, outdoors + coffee"
"NYC, Sunday, $60, art + brunch, no chains"
"Chicago, Saturday, $80, waterfront + local food"
```

### Tool Failure Handling
- Tavily timeout → retry once, then return partial candidates with warning
- Nominatim fail → stop added without lat/lng, excluded from map
- Gemini fail → surface error to user with retry option

---

## Observability (per request)

```json
{
  "scout_latency_ms": 3200,
  "planner_latency_ms": 2100,
  "eval_latency_ms": 800,
  "total_latency_ms": 6100,
  "tavily_searches": 2,
  "total_tokens": 2460,
  "estimated_cost_usd": 0.0002,
  "trajectory": [
    { "node": "scout", "candidates_returned": 9, "tokens": 1200, "latency_ms": 3200 },
    { "node": "planner", "stops_selected": 5, "budget_used": 67, "tokens": 1260, "latency_ms": 2100 },
    { "node": "eval", "latency_ms": 800 }
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
| AI | Gemini 2.5 Flash (Google AI Studio) | Yes (1500 req/day) |
| Web Search | Tavily | Yes (1000 searches/mo) |
| Geocoding | Nominatim (OpenStreetMap) | Yes, no key |
| Map rendering | Leaflet.js | Yes |
| Render keep-alive | cron-job.org ping /health every 10 min | Yes |

---

## UI Design

### Input Page (/)
- City text input
- Date picker
- Budget slider ($20 - $200)
- Vibe tag chips: [outdoors] [coffee] [local eats] [art] [nightlife] [family-friendly]
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
│  Trajectory per node                   │
└────────────────────────────────────────┘
```

Each stop card shows: name, time slot, dwell time, travel to next, estimated cost, vibe reason, disclaimer "Verify hours before visiting"

---

## Out of Scope (V1)

- Opening hours verification → disclaimer on each card
- User accounts / saved trips
- Booking links
- Real routing API (Haversine + speed estimate instead)
- Mobile app
- Multi-day trips
- Chat interface (V2: "refine my itinerary" input after generation)

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
│   ├── main.py                    # FastAPI + /health + /plan
│   ├── models.py                  # Pydantic schemas + TripState
│   ├── graph.py                   # LangGraph graph definition
│   ├── nodes/
│   │   ├── scout.py               # scout_node
│   │   ├── planner.py             # planner_node
│   │   └── eval.py                # eval_node
│   ├── evals/
│   │   ├── rule_based.py          # Deterministic checks
│   │   └── llm_judge.py           # LLM-as-judge scoring
│   ├── utils/
│   │   ├── geocode.py             # Nominatim wrapper
│   │   └── haversine.py           # Travel time calc
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
Day 1   Setup: scaffold frontend + backend, all API keys wired, /health live   [DONE]
Day 2   LangGraph: define TripState, graph, wire scout_node with Tavily
Day 3   planner_node: Nominatim geocoding, Haversine, schedule builder
Day 4   eval_node: rule-based + LLM-as-judge + trajectory logging
Day 5   Golden test set, tool failure handling, observability complete
Day 6   Next.js UI: input form with shadcn/ui (slider, chips, date picker)
Day 7   Results page: itinerary cards + budget bar
Day 8   Map view: Leaflet + Nominatim pins
Day 9   Dev panel (evals + trajectory), deploy Vercel + Render + cron ping
Day 10  Edge case testing, polish, README
```

---

## API Keys Needed

- `GOOGLE_AI_API_KEY` — Gemini 2.5 Flash (Google AI Studio)
- `TAVILY_API_KEY` — Tavily search
- Nominatim — no key, use `User-Agent` header, rate limit 1 req/sec

---

## Key Interview Talking Points This Project Covers

- Why LangGraph over custom agents (state, observability, retries, industry standard)
- Trajectory evaluation vs output-only evaluation
- LLM-as-judge for subjective quality scoring
- Golden test sets for regression detection
- Tool failure handling and graceful degradation
- Cost + latency tracking per agent node
- When NOT to use agents (single LLM call would suffice)
