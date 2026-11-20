export default function BudgetBar({ spent, budget }: { spent: number; budget: number }) {
  const pct = Math.min((spent / budget) * 100, 100);
  const over = spent > budget;

  return (
    <div className="bg-white rounded-2xl p-4 shadow-sm shadow-stone-100">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium">Budget</span>
        <span
          className="text-sm font-semibold"
          style={{ color: over ? "#E53E3E" : "var(--accent)" }}
        >
          ${spent.toFixed(0)} / ${budget}
        </span>
      </div>
      <div className="h-2.5 rounded-full" style={{ background: "var(--border)" }}>
        <div
          className="h-2.5 rounded-full transition-all"
          style={{
            width: `${pct}%`,
            background: over ? "#E53E3E" : "var(--accent)",
          }}
        />
      </div>
    </div>
  );
}
