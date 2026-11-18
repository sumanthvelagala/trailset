# Trailset

AI-powered day-trip concierge. Enter a city, budget, and vibe — get a timed itinerary with a map.

## Stack

- **Frontend** — Next.js (Vercel)
- **Backend** — FastAPI (Render)
- **AI** — Gemini 2.5 Flash (free tier)
- **Search** — Tavily (free tier)
- **Geocoding** — Nominatim / OpenStreetMap (free, no key)
- **Maps** — Leaflet.js (free)

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
cp ../.env.example .env.local  # fill in NEXT_PUBLIC_API_URL
npm run dev
```

## API Keys Needed

| Key | Where to get |
|---|---|
| `GOOGLE_AI_API_KEY` | [Google AI Studio](https://aistudio.google.com) |
| `TAVILY_API_KEY` | [Tavily](https://tavily.com) |

Nominatim requires no key — just include a `User-Agent` header.

## Project Plan

See [PLAN.md](./PLAN.md) for full architecture, agent design, evals, and build plan.
