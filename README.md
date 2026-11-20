# Trailset

AI-powered day-trip concierge. Enter a city, budget, and vibe — get a timed itinerary with source links.

## Stack

| Layer | Tool |
|---|---|
| Frontend | Next.js → Vercel |
| Backend | FastAPI → Render |
| Agent orchestration | LangGraph |
| AI (scout / planner / eval) | Gemini 3.5 Flash Lite · fallback: 3.1 Flash Lite on 503 |
| Web search | LangSearch (~950 searches/day free) |
| Video search | YouTube Data API v3 (10,000 units/day free) |
| Geocoding | HERE Geocoding (primary) + Nominatim fallback |
| Routing | HERE Routing API (traffic-aware travel times) |
| Rate limiting + storage | Upstash Redis |

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in your keys
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Keys Needed

| Variable | Service | Where to get |
|---|---|---|
| `GOOGLE_AI_API_KEY` | Gemini LLM | [aistudio.google.com](https://aistudio.google.com) |
| `LANGSEARCH_API_KEY` | Web search | [langsearch.com](https://langsearch.com) |
| `YOUTUBE_API_KEY` | YouTube Data API v3 | [console.cloud.google.com](https://console.cloud.google.com) |
| `HERE_API_KEY` | Geocoding + routing | [developer.here.com](https://developer.here.com) (free, no credit card) |
| `UPSTASH_REDIS_REST_URL` | Trip storage | [upstash.com](https://upstash.com) |
| `UPSTASH_REDIS_REST_TOKEN` | Trip storage | same Upstash dashboard |
| `REDIS_URL` | Rate limiting | same Upstash dashboard (standard Redis URL) |

Frontend needs one env var:
```
NEXT_PUBLIC_API_URL=https://your-render-backend.onrender.com
```

## Populating Home Page Examples

After deploy, run once to populate Redis with curated example trips:
```bash
cd backend
python run_examples.py
```

## Project Plan

See [PLAN.md](./PLAN.md) for full architecture, agent design, evals, and build plan.
