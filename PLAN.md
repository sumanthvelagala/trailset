# Daytripper — Project Plan

> AI-powered single-day trip concierge. Enter a city, date, budget, and vibe — get a realistic, timed itinerary with a map.

---

## Product

**Input:** City · Date · Budget ($) · Vibe (free text)
**Output:** Timed itinerary cards + map with pins + budget bar + eval results

**Example:**
```
City:   Austin
Date:   Saturday, Nov 22
Budget: $100
Vibe:   outdoors + good coffee, no tourist traps
```

---

## Agent Architecture

### Scout Agent
- Runs 2 parallel Tavily searches:
  - `"{city} best local coffee brunch lunch not touristy"`
  - `"{city} outdoor activities parks hidden gems {day}"`
- Returns 8-10 candidates: `name, type, neighborhood, est_cost, description`

### Planner Agent
- Takes Scout candidates
- Geocodes each via Nominatim (OSM) → lat/lng
- Assigns dwell time by place type:
  - Coffee shop → 30-45 min
  - Brunch/lunch → 45-60 min
  - Park/hiking → 90-120 min
  - Outdoor activity → 60-90 min
  - Market/browse → 30-45 min
- Calculates travel time: Haversine distance + speed estimate (driving ~20mph / walking ~20 min per mile)
- Builds timed schedule: picks 4-5 stops, assigns start times, travel legs
- Validates: total cost ≤ budget, no overlapping slots, gaps ≥ 20 min

**Output format per stop:**
```json
{
  "name": "Barton Springs Pool",
  "type": "outdoor_activity",
  "address": "2201 Barton Springs Rd, Austin",
  "lat": 30.2638,
  "lng": -97.7714,
  "start_time": "10:53am",
  "dwell_min": 120,
  "travel_to_next_min": 12,
  "est_cost": 5,
  "vibe_reason": "Local favorite, not on tourist maps, outdoors"
}
```

---

## Evals (run after every generation)

| Eval | Type | Logic |
|---|---|---|
| Budget adherence | Rule-based | sum(costs) <= user budget |
| City correctness | Rule-based | all addresses contain city name |
| Schedule feasibility | Rule-based | no overlaps, gaps >= 20 min |
| Stop count | Rule-based | 3 <= stops <= 6 |
| Vibe match | LLM-as-judge | Gemini scores 1-5 vs vibe input |
| Relevance | LLM-as-judge | are places actually local/non-touristy |

---

## Observability (per request)

```json
{
  "scout_latency_ms": 3200,
  "planner_latency_ms": 2100,
  "total_latency_ms": 5300,
  "tavily_searches": 2,
  "input_tokens": 1840,
  "output_tokens": 620,
  "estimated_cost_usd": 0.0002,
  "eval_scores": {
    "budget_ok": true,
    "city_ok": true,
    "schedule_ok": true,
    "stop_count_ok": true,
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
| Backend | FastAPI → Render.com | Yes (sleeps after 15 min) |
| AI | Gemini 2.5 Flash (Google AI Studio) | Yes (1500 req/day) |
| Web Search | Tavily | Yes (1000 searches/mo) |
| Geocoding | Nominatim (OpenStreetMap) | Yes, no key needed |
| Map rendering | Leaflet.js | Yes |
| Render keep-alive | cron-job.org ping /health every 10 min | Yes |

---

## Out of Scope (V1)

- Opening hours verification — show disclaimer: "Verify hours before visiting"
- User accounts / saved trips
- Booking links
- Real routing API (Haversine + speed estimate instead)
- Mobile app
- Multi-day trips

---

## Project Structure

```
daytripper/
├── frontend/          # Next.js app
│   ├── app/
│   │   ├── page.tsx           # Input form
│   │   └── results/page.tsx   # Itinerary + map
│   └── components/
│       ├── ItineraryCard.tsx
│       ├── MapView.tsx
│       ├── BudgetBar.tsx
│       └── DevPanel.tsx       # Evals + observability
├── backend/           # FastAPI
│   ├── main.py
│   ├── agents/
│   │   ├── scout.py           # Tavily searches
│   │   └── planner.py         # Schedule builder
│   ├── evals/
│   │   ├── rule_based.py
│   │   └── llm_judge.py
│   ├── utils/
│   │   ├── geocode.py         # Nominatim wrapper
│   │   └── haversine.py       # Travel time calc
│   └── models.py              # Pydantic schemas
└── PLAN.md
```

---

## 10-Day Build Plan

```
Day 1   Setup: scaffold frontend + backend, wire all API keys, /health endpoint
Day 2   Scout Agent: Tavily integration, parallel searches, candidate output
Day 3   Planner Agent: Nominatim geocoding, dwell times, Haversine travel time
Day 4   Planner Agent: schedule builder, budget validation, final JSON output
Day 5   Rule-based evals + observability (latency, tokens, cost tracking)
Day 6   LLM-as-judge evals (vibe match, relevance)
Day 7   Next.js UI: input form + itinerary cards
Day 8   Map view: Leaflet + Nominatim pins, budget bar
Day 9   Dev panel (evals + observability), deploy Vercel + Render + cron ping
Day 10  Edge case testing, polish, README
```

---

## API Keys Needed

- `GOOGLE_AI_API_KEY` — Gemini 2.5 Flash (Google AI Studio)
- `TAVILY_API_KEY` — Tavily search
- Nominatim — no key, use `User-Agent` header, rate limit 1 req/sec
