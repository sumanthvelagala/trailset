
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
  image_url: string | null;
}

const TYPE_LABEL: Record<string, string> = {
  coffee: "Coffee",
  food: "Food",
  outdoor_activity: "Outdoors",
  park: "Park",
  market: "Market",
};

const TYPE_EMOJI: Record<string, string> = {
  coffee: "☕",
  food: "🍜",
  outdoor_activity: "🏃",
  park: "🌳",
  market: "🛍️",
};

const MODE_ICON: Record<string, string> = {
  walk: "🚶",
  drive: "🚗",
};

export default function StopCard({
  stop,
  index,
  isLast,
}: {
  stop: Stop;
  index: number;
  isLast: boolean;
}) {
  return (
    <div className="flex gap-3">

      {/* Timeline */}
      <div className="flex flex-col items-center pt-1 shrink-0">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold"
          style={{ background: "var(--accent)" }}
        >
          {index + 1}
        </div>
        {!isLast && (
          <div
            className="w-px flex-1 mt-2"
            style={{ borderLeft: "2px dashed var(--accent)", minHeight: "40px", opacity: 0.3 }}
          />
        )}
      </div>

      {/* Card */}
      <div className="flex-1 bg-white rounded-2xl shadow-sm overflow-hidden mb-3"
        style={{ boxShadow: "0 1px 8px rgba(0,0,0,0.06)" }}>

        {/* Header image — only shown if Tavily returned one */}
        {stop.image_url && (
          <div className="relative h-36 w-full overflow-hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={stop.image_url}
              alt={stop.name}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.3), transparent)" }} />
          </div>
        )}

        <div className="p-5">

          {/* Top row: time + cost */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full text-white"
                style={{ background: "var(--accent)" }}>
                {stop.start_time}
              </span>
              <span className="text-xs" style={{ color: "var(--muted)" }}>
                → {stop.end_time}
              </span>
              <span className="text-xs" style={{ color: "var(--muted)" }}>
                · {stop.dwell_minutes} min
              </span>
            </div>
            <span className="text-sm font-bold" style={{ color: "var(--accent)" }}>
              {stop.est_cost === 0 ? "Free" : `$${stop.est_cost.toFixed(0)}`}
              {!stop.cost_verified && stop.est_cost > 0 && (
                <span className="text-xs font-normal ml-0.5" style={{ color: "var(--muted)" }}>~</span>
              )}
            </span>
          </div>

          {/* Name + type badge */}
          <div className="flex items-start gap-2 mb-1">
            <h3 className="text-base font-semibold leading-snug">{stop.name}</h3>
            <span className="text-xs px-2 py-0.5 rounded-full shrink-0 mt-0.5"
              style={{ background: "var(--background)", color: "var(--muted)", border: "1px solid var(--border)" }}>
              {TYPE_EMOJI[stop.type]} {TYPE_LABEL[stop.type] ?? stop.type}
            </span>
          </div>

          {/* Neighborhood */}
          <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
            📍 {stop.neighborhood}
          </p>

          {/* Reason */}
          <p className="text-sm leading-relaxed text-gray-700">{stop.reason}</p>

          {/* Snippets */}
          {stop.snippets.length > 0 && (
            <div className="mt-3 flex flex-col gap-1.5">
              {stop.snippets.slice(0, 2).map((s, i) => (
                <p key={i} className="text-xs italic pl-3 leading-relaxed"
                  style={{ color: "var(--muted)", borderLeft: "2px solid var(--border)" }}>
                  "{s}"
                </p>
              ))}
            </div>
          )}

        </div>

        {/* Travel to next */}
        {!isLast && stop.travel_to_next_minutes > 0 && (
          <div className="px-5 py-3 flex items-center gap-2 text-xs"
            style={{ background: "var(--background)", borderTop: "1px solid var(--border)", color: "var(--muted)" }}>
            <span>{MODE_ICON[stop.travel_mode] ?? "🚗"}</span>
            <span>
              <strong>{stop.travel_to_next_minutes} min</strong> {stop.travel_mode} to next stop
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
