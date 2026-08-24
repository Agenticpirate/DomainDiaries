import { STATS } from "../../data/directory";
import { formatPct } from "../../lib/format";
import { Spark } from "../ui/Spark";

const COLORS = {
  violet: "#9b7dff",
  cyan: "#3ee7ff",
  gold: "#f5c542",
  pink: "#ff4d9d",
};

export function MarketOverview() {
  return (
    <section className="glass rounded-[28px] p-5">
      <h2 className="text-sm font-semibold">Market Overview</h2>
      <div className="mt-4 grid grid-cols-2 gap-3">
        {STATS.map((stat) => (
          <article key={stat.label} className="rounded-2xl border border-[var(--line)] bg-black/10 p-3">
            <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--mute)]">{stat.label}</p>
            <p className="mt-1 font-display text-lg font-bold">{stat.value}</p>
            <div className="mt-1 flex items-center justify-between">
              <span className="font-mono text-xs text-[var(--green)]">{formatPct(stat.change)}</span>
              <Spark values={stat.spark} color={COLORS[stat.tone]} />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
