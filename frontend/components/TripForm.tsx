"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const VIBE_TAGS = [
  { id: "outdoors", label: "Outdoors" },
  { id: "coffee", label: "Coffee" },
  { id: "local eats", label: "Local eats" },
  { id: "art", label: "Art" },
  { id: "nightlife", label: "Nightlife" },
  { id: "family-friendly", label: "Family-friendly" },
];

const MAX_FREE_TEXT = 100;
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getBudgetLabel(budget: number): { label: string; color: string; bg: string } {
  if (budget <= 50) return { label: "Budget", color: "#E8445A", bg: "#FEE2E6" };
  if (budget <= 120) return { label: "Comfortable", color: "#C03048", bg: "#FCCDD4" };
  return { label: "Splurge", color: "#9B1F33", bg: "#F9A8B4" };
}

export default function TripForm() {
  const router = useRouter();

  const [city, setCity] = useState("");
  const [date, setDate] = useState("");
  const [budget, setBudget] = useState(80);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");
  const [startLocation, setStartLocation] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function toggleTag(id: string) {
    setSelectedTags((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!city.trim()) return setError("City is required.");
    if (!date) return setError("Date is required.");
    if (selectedTags.length === 0) return setError("Pick at least one vibe.");

    const vibe = [selectedTags.join(", "), freeText.trim()]
      .filter(Boolean)
      .join(". ");

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          city: city.trim(),
          date,
          budget,
          vibe,
          start_location: startLocation.trim() || null,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `Error ${res.status}`);
      }

      const result = await res.json();
      sessionStorage.setItem("trailset_result", JSON.stringify(result));
      sessionStorage.setItem("trailset_input", JSON.stringify({ city, date, budget, vibe }));
      router.push("/results");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  const remaining = MAX_FREE_TEXT - freeText.length;
  const budgetLabel = getBudgetLabel(budget);

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6">

      {/* City */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-semibold">City</label>
        <div className="relative">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
              <circle cx="12" cy="9" r="2.5"/>
            </svg>
          </span>
          <input
            type="text"
            placeholder="Lisbon, Portland, Kyoto..."
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="w-full rounded-xl border pl-10 pr-4 py-3 text-sm outline-none transition focus:ring-2"
            style={{ borderColor: "var(--border)", "--tw-ring-color": "#F9A8B0" } as React.CSSProperties}
          />
        </div>
      </div>

      {/* Date */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-semibold">Date</label>
        <div className="relative">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2"/>
              <path d="M16 2v4M8 2v4M3 10h18"/>
            </svg>
          </span>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full rounded-xl border pl-10 pr-4 py-3 text-sm outline-none transition focus:ring-2"
            style={{ borderColor: "var(--border)" }}
          />
        </div>
      </div>

      {/* Budget slider */}
      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <label className="text-sm font-semibold">Daily budget</label>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold">${budget}</span>
            <span
              className="text-xs font-semibold px-2.5 py-1 rounded-full"
              style={{ background: budgetLabel.bg, color: budgetLabel.color }}
            >
              {budgetLabel.label}
            </span>
          </div>
        </div>
        <input
          type="range"
          min={20}
          max={200}
          step={5}
          value={budget}
          onChange={(e) => setBudget(Number(e.target.value))}
        />
        <div className="flex justify-between text-xs" style={{ color: "var(--muted)" }}>
          <span>$20</span>
          <span>$200</span>
        </div>
      </div>

      {/* Vibe chips */}
      <div className="flex flex-col gap-2">
        <div>
          <label className="text-sm font-semibold">Vibe</label>
          <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>Pick as many as you like.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {VIBE_TAGS.map((tag) => {
            const active = selectedTags.includes(tag.id);
            return (
              <button
                key={tag.id}
                type="button"
                onClick={() => toggleTag(tag.id)}
                className="rounded-full px-4 py-1.5 text-sm border transition-all"
                style={{
                  background: active ? "var(--accent)" : "white",
                  color: active ? "white" : "var(--foreground)",
                  borderColor: active ? "var(--accent)" : "var(--border)",
                  fontWeight: active ? 600 : 400,
                }}
              >
                {tag.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Free text */}
      <div className="flex flex-col gap-1.5">
        <div className="flex justify-between items-center">
          <label className="text-sm font-semibold">
            Anything else?{" "}
            <span className="font-normal" style={{ color: "var(--muted)" }}>(optional)</span>
          </label>
          <span className="text-xs" style={{ color: remaining <= 10 ? "#E8445A" : "var(--muted)" }}>
            {freeText.length}/{MAX_FREE_TEXT}
          </span>
        </div>
        <textarea
          rows={2}
          placeholder="Vegetarian, hate crowds, love a good view..."
          value={freeText}
          onChange={(e) => setFreeText(e.target.value.slice(0, MAX_FREE_TEXT))}
          className="w-full rounded-xl border px-4 py-3 text-sm outline-none transition resize-none focus:ring-2"
          style={{ borderColor: "var(--border)" }}
        />
      </div>

      {/* Starting location */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-semibold">
          Starting location{" "}
          <span className="font-normal" style={{ color: "var(--muted)" }}>(optional)</span>
        </label>
        <div className="relative">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L19 21l-7-4-7 4L12 2z"/>
            </svg>
          </span>
          <input
            type="text"
            placeholder="Hotel, neighborhood, or address"
            value={startLocation}
            onChange={(e) => setStartLocation(e.target.value)}
            className="w-full rounded-xl border pl-10 pr-4 py-3 text-sm outline-none transition focus:ring-2"
            style={{ borderColor: "var(--border)" }}
          />
        </div>
        <p className="text-xs" style={{ color: "var(--muted)" }}>We'll route the day from here.</p>
      </div>

      {/* Error */}
      {error && <p className="text-sm text-red-500 -mt-2">{error}</p>}

      {/* Submit */}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-xl py-3.5 text-sm font-semibold text-white transition-all disabled:opacity-60 flex items-center justify-center gap-2 mt-1"
        style={{ background: "var(--accent)" }}
      >
        {loading ? (
          <>
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            Planning your day…
          </>
        ) : (
          "Plan my trip"
        )}
      </button>

      {loading && (
        <p className="text-xs text-center -mt-3" style={{ color: "var(--muted)" }}>
          Searching places · building route · scoring itinerary (~10–15s)
        </p>
      )}
    </form>
  );
}
