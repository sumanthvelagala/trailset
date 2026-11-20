"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import BudgetBar from "@/components/BudgetBar";
import DevPanel from "@/components/DevPanel";
import VintageRoute from "@/components/VintageRoute";

interface Stop {
  name: string;
  type: string;
  neighborhood: string;
  start_time: string;
  end_time: string;
  dwell_minutes: number;
  travel_to_next_minutes: number;
  travel_mode: string;
  est_cost: number;
  cost_verified: boolean;
  lat: number | null;
  lng: number | null;
  reason: string;
  snippets: string[];
  source_videos: { title: string; url: string; channel: string }[];
  source_urls: { title: string; url: string }[];
  image_url: string | null;
}

interface TripResult {
  stops: Stop[];
  total_cost: number;
  budget: number;
  eval_scores: Record<string, unknown>;
  observability: {
    total_latency_ms: number;
    tavily_searches: number;
    route_calls: number;
    total_tokens: number;
    estimated_cost_usd: number;
    trajectory: unknown[];
  };
}

export default function ResultsPage() {
  const router = useRouter();
  const [result, setResult] = useState<TripResult | null>(null);
  const [input, setInput] = useState<{ city: string; date: string } | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem("trailset_result");
    const rawInput = sessionStorage.getItem("trailset_input");

    if (!raw) {
      if (process.env.NODE_ENV === "development") {
        fetch("/mock-result.json")
          .then((r) => r.json())
          .then((data) => {
            setResult(data);
            setInput({ city: "Austin", date: "Saturday, Nov 22" });
          });
        return;
      }
      router.push("/");
      return;
    }

    setResult(JSON.parse(raw));
    if (rawInput) setInput(JSON.parse(rawInput));
  }, [router]);

  if (!result) return null;

  const { stops, total_cost, budget, eval_scores, observability } = result;

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--background)" }}>

      {/* Header */}
      <header
        className="sticky top-0 z-20 bg-white border-b px-6 py-3 flex items-center justify-between"
        style={{ borderColor: "var(--border)" }}
      >
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-1.5 text-sm font-medium hover:opacity-70 transition-opacity"
          style={{ color: "var(--accent)" }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M19 12H5M5 12l7-7M5 12l7 7" />
          </svg>
          New trip
        </button>

        <div className="text-center">
          <p className="text-sm font-semibold">{input?.city}</p>
          <p className="text-xs" style={{ color: "var(--muted)" }}>{input?.date}</p>
        </div>

        <div className="flex items-center gap-1.5 text-sm font-medium" style={{ color: "var(--muted)" }}>
          <span>{stops.length} stops</span>
          <span>·</span>
          <span style={{ color: "var(--accent)", fontWeight: 600 }}>${total_cost.toFixed(0)}</span>
        </div>
      </header>

      {/* Body */}
      <div className="flex-1 w-full max-w-2xl mx-auto px-4 py-8 flex flex-col gap-5">
        <BudgetBar spent={total_cost} budget={budget} />
        <VintageRoute stops={stops} city={input?.city ?? ""} />
        <p className="text-xs text-center" style={{ color: "var(--muted)" }}>
          Verify opening hours before visiting · AI-generated itinerary
        </p>
        <DevPanel evalScores={eval_scores} observability={observability} />
      </div>

    </div>
  );
}
