"use client";

interface SourceVideo {
  title: string;
  url: string;
  channel: string;
}

interface SourceUrl {
  title: string;
  url: string;
}

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
  reason: string;
  snippets: string[];
  source_videos: SourceVideo[];
  source_urls: SourceUrl[];
  lat: number | null;
  lng: number | null;
}

const TYPE_EMOJI: Record<string, string> = {
  coffee: "☕",
  food: "🍽",
  outdoor_activity: "🌿",
  park: "🌳",
  market: "🛒",
};

const TYPE_LABEL: Record<string, string> = {
  coffee: "Coffee",
  food: "Food",
  outdoor_activity: "Outdoors",
  park: "Park",
  market: "Market",
};

// ── Stop card ─────────────────────────────────────────────────────────────────

function RouteCard({ stop, index, side }: { stop: Stop; index: number; side: "left" | "right" }) {
  return (
    <div
      className={`w-[72%] ${side === "right" ? "ml-auto" : "mr-auto"}`}
      style={{
        background: "white",
        border: "1px solid var(--border)",
        borderRadius: 16,
        padding: "18px 20px",
        boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
      }}
    >
      {/* Pin + name */}
      <div className="flex items-start gap-3 mb-3">
        <div
          style={{
            background: "var(--accent)",
            color: "white",
            width: 28,
            height: 28,
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700,
            fontSize: 12,
            flexShrink: 0,
            boxShadow: "0 2px 6px rgba(232,68,90,0.3)",
          }}
        >
          {index + 1}
        </div>
        <div className="flex-1 min-w-0">
          <h3 style={{ fontWeight: 700, fontSize: 15, color: "var(--foreground)", lineHeight: 1.25 }}>
            {stop.name}
          </h3>
          <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>
            📍 {stop.neighborhood}
          </p>
        </div>
        <span style={{ fontWeight: 700, fontSize: 14, color: "var(--accent)", flexShrink: 0 }}>
          {stop.est_cost === 0 ? "Free" : `$${stop.est_cost.toFixed(0)}`}
          {!stop.cost_verified && stop.est_cost > 0 && (
            <span style={{ fontSize: 11, fontWeight: 400, color: "var(--muted)" }}>~</span>
          )}
        </span>
      </div>

      {/* Time + type */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span
          style={{
            background: "var(--background)",
            color: "var(--accent)",
            fontSize: 11,
            fontWeight: 600,
            padding: "3px 10px",
            borderRadius: 20,
            border: "1px solid var(--border)",
          }}
        >
          {stop.start_time} → {stop.end_time} · {stop.dwell_minutes} min
        </span>
        <span
          style={{
            background: "var(--background)",
            color: "var(--muted)",
            fontSize: 11,
            padding: "3px 10px",
            borderRadius: 20,
            border: "1px solid var(--border)",
          }}
        >
          {TYPE_EMOJI[stop.type]} {TYPE_LABEL[stop.type] ?? stop.type}
        </span>
      </div>

      {/* Reason */}
      <p style={{ fontSize: 13, color: "#374151", lineHeight: 1.55 }}>{stop.reason}</p>

      {/* Snippets */}
      {stop.snippets.length > 0 && (
        <div className="mt-2.5 flex flex-col gap-1.5">
          {stop.snippets.slice(0, 2).map((s, i) => (
            <p
              key={i}
              style={{
                fontSize: 11,
                color: "var(--muted)",
                fontStyle: "italic",
                paddingLeft: 10,
                borderLeft: "2px solid var(--border)",
                lineHeight: 1.5,
              }}
            >
              &ldquo;{s}&rdquo;
            </p>
          ))}
        </div>
      )}

      {/* Sources: web + YouTube links */}
      {((stop.source_urls?.length ?? 0) > 0 || (stop.source_videos?.length ?? 0) > 0) && (
        <div className="mt-2.5 flex flex-col gap-1">
          {stop.source_urls?.slice(0, 2).map((s, i) => (
            <a
              key={`web-${i}`}
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 11,
                color: "var(--muted)",
                textDecoration: "none",
              }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.6">
                <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
              </svg>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {s.title}
              </span>
            </a>
          ))}
          {stop.source_videos?.slice(0, 1).map((v, i) => (
            <a
              key={`yt-${i}`}
              href={v.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 11,
                color: "var(--muted)",
                textDecoration: "none",
              }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="var(--accent)" opacity="0.7">
                <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"/>
              </svg>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {v.title}
              </span>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

// ── SVG curving road connector ────────────────────────────────────────────────

function RoadConnector({
  fromSide,
  toSide,
  minutes,
  mode,
}: {
  fromSide: "left" | "right";
  toSide: "left" | "right";
  minutes: number;
  mode: string;
}) {
  // Cards are 72% wide. Left center ≈ 36%, right center ≈ 64%
  const leftX = 36;
  const rightX = 64;
  const startX = fromSide === "left" ? leftX : rightX;
  const endX = toSide === "left" ? leftX : rightX;

  const path = `M ${startX} 0 C ${startX} 65 ${endX} 35 ${endX} 100`;

  return (
    <div style={{ position: "relative", height: 80 }}>
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{ position: "absolute", inset: 0 }}
      >
        <path
          d={path}
          fill="none"
          stroke="var(--accent)"
          strokeWidth="1.8"
          strokeDasharray="5 5"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
          opacity="0.45"
        />
      </svg>

      {/* Travel time badge */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          background: "white",
          border: "1px solid var(--border)",
          borderRadius: 20,
          padding: "3px 10px",
          fontSize: 11,
          fontWeight: 600,
          color: "var(--muted)",
          whiteSpace: "nowrap",
          boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
        }}
      >
        {mode === "walk" ? "🚶" : "🚗"} {minutes} min
      </div>
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function VintageRoute({ stops, city }: { stops: Stop[]; city: string }) {
  // Use lat/lng when available (accurate), fall back to name+city string
  const googleMapsUrl = stops
    .map((s) =>
      s.lat && s.lng
        ? `${s.lat},${s.lng}`
        : encodeURIComponent(`${s.name}, ${city}`)
    )
    .join("/");

  const sides = stops.map((_, i): "left" | "right" => (i % 2 === 0 ? "left" : "right"));

  return (
    <div className="flex flex-col">
      {stops.map((stop, i) => (
        <div key={i}>
          <RouteCard stop={stop} index={i} side={sides[i]} />
          {i < stops.length - 1 && (
            <RoadConnector
              fromSide={sides[i]}
              toSide={sides[i + 1]}
              minutes={stop.travel_to_next_minutes}
              mode={stop.travel_mode}
            />
          )}
        </div>
      ))}

      {/* Google Maps button */}
      <a
        href={`https://www.google.com/maps/dir/${googleMapsUrl}`}
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          marginTop: 28,
          padding: "13px",
          borderRadius: 14,
          background: "var(--accent)",
          color: "white",
          fontWeight: 700,
          fontSize: 14,
          textDecoration: "none",
          boxShadow: "0 2px 10px rgba(232,68,90,0.25)",
        }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
        </svg>
        Open full route in Google Maps
      </a>
    </div>
  );
}
