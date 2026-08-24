import { formatCompact, formatPct } from "../../lib/format";
import { cn } from "../../lib/cn";
import type { FearGreed, GlobalMarket } from "../../types";

type Props = {
  global: GlobalMarket | null;
  fng: FearGreed | null;
};

export function StatStrip({ global, fng }: Props) {
  const data = global?.data;
  const fear = fng?.data?.[0];
  const cards = [
    {
      label: "Market cap",
      value: data ? `$${formatCompact(data.total_market_cap.usd)}` : "—",
      hint: data ? formatPct(data.market_cap_change_percentage_24h_usd) : "",
      up: (data?.market_cap_change_percentage_24h_usd ?? 0) >= 0,
    },
    {
      label: "24h volume",
      value: data ? `$${formatCompact(data.total_volume.usd)}` : "—",
      hint: data ? `${data.active_cryptocurrencies.toLocaleString()} assets` : "",
      up: true,
    },
    {
      label: "BTC dominance",
      value: data ? `${data.market_cap_percentage.btc.toFixed(1)}%` : "—",
      hint: data ? `ETH ${data.market_cap_percentage.eth.toFixed(1)}%` : "",
      up: true,
    },
    {
      label: "Fear & greed",
      value: fear ? fear.value : "—",
      hint: fear?.value_classification ?? "",
      up: Number(fear?.value ?? 50) >= 50,
    },
  ];

  return (
    <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {cards.map((card) => (
        <article key={card.label} className="stat-card hairline rounded-2xl bg-paper/80 p-4">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-mute">{card.label}</p>
          <p className="mt-2 font-mono text-2xl tracking-tight">{card.value}</p>
          <p className={cn("mt-1 font-mono text-xs", card.up ? "text-up" : "text-down")}>{card.hint}</p>
        </article>
      ))}
    </section>
  );
}
