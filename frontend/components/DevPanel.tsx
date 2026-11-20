"use client";

import { useState } from "react";

interface Observability {
  total_latency_ms: number;
  tavily_searches: number;
  route_calls: number;
  total_tokens: number;
  estimated_cost_usd: number;
  trajectory: unknown[];
}

export default function DevPanel({
  evalScores,
  observability,
}: {
  evalScores: Record<string, unknown>;
  observability: Observability;
}) {
  const [open, setOpen] = useState(false);

  const checks = [
    { key: "budget_ok", label: "budget" },
    { key: "stop_count_ok", label: "stop count" },
    { key: "schedule_ok", label: "schedule" },
    { key: "scout_coverage_ok", label: "scout coverage" },
    { key: "has_coords_ok", label: "coords" },
  ];

  return (
    <div className="rounded-2xl border overflow-hidden" style={{ borderColor: "var(--border)" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white text-sm font-medium hover:bg-stone-50 transition"
      >
        <span>⚙️ Dev Panel</span>
        <span style={{ color: "var(--muted)" }}>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="bg-white border-t px-4 py-4 flex flex-col gap-4" style={{ borderColor: "var(--border)" }}>

          {/* Performance */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "var(--muted)" }}>
              Performance
            </p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <Stat label="Total latency" value={`${(observability.total_latency_ms / 1000).toFixed(1)}s`} />
              <Stat label="Tavily searches" value={String(observability.tavily_searches)} />
              <Stat label="Route calls" value={String(observability.route_calls)} />
              <Stat label="Tokens" value={observability.total_tokens.toLocaleString()} />
              <Stat label="Est. cost" value={`$${observability.estimated_cost_usd.toFixed(5)}`} />
            </div>
          </div>

          {/* Evals */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "var(--muted)" }}>
              Evals
            </p>
            <div className="flex flex-wrap gap-2 mb-2">
              {checks.map(({ key, label }) => (
                <span
                  key={key}
                  className="text-xs px-2.5 py-1 rounded-full font-medium"
                  style={{
                    background: evalScores[key] ? "#D1FAE5" : "#FEE2E2",
                    color: evalScores[key] ? "#065F46" : "#991B1B",
                  }}
                >
                  {evalScores[key] ? "✓" : "✗"} {label}
                </span>
              ))}
            </div>
            <div className="text-sm flex gap-4">
              <span>Vibe match: <strong>{String(evalScores.vibe_match ?? "—")}/5</strong></span>
              <span>Relevance: <strong>{String(evalScores.relevance ?? "—")}/5</strong></span>
            </div>
            {evalScores.reasoning ? (
              <p className="text-xs mt-1 italic" style={{ color: "var(--muted)" }}>
                {String(evalScores.reasoning)}
              </p>
            ) : null}
          </div>

          {/* Trajectory */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "var(--muted)" }}>
              Trajectory
            </p>
            <div className="flex flex-col gap-1">
              {(observability.trajectory as Array<Record<string, unknown>>).map((t, i) => {
                const parts: string[] = [];
                if (t.latency_ms != null) parts.push(`${String(t.latency_ms)}ms`);
                if (t.tokens != null) parts.push(`${String(t.tokens)} tokens`);
                if (t.candidates_returned != null) parts.push(`${String(t.candidates_returned)} candidates`);
                if (t.stops_selected != null) parts.push(`${String(t.stops_selected)} stops`);
                if (t.route_calls != null) parts.push(`${String(t.route_calls)} routes`);
                return (
                  <div key={i} className="text-xs flex gap-2 items-baseline">
                    <span
                      className="font-mono px-1.5 py-0.5 rounded"
                      style={{ background: "var(--background)", color: "var(--accent)" }}
                    >
                      {String(t.node)}
                    </span>
                    <span style={{ color: "var(--muted)" }}>{parts.join(" · ")}</span>
                  </div>
                );
              })}
            </div>
          </div>

        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs" style={{ color: "var(--muted)" }}>{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}
