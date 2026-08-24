import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Star } from "lucide-react";
import { fetchChart, fetchCoin } from "../lib/api";
import { formatCompact, formatUsd } from "../lib/format";
import { cn } from "../lib/cn";
import { useWatchlist } from "../hooks/useWatchlist";
import { PriceChart } from "../components/coin/PriceChart";
import { PriceChange } from "../components/markets/PriceChange";
import type { ChartPoint, CoinDetail } from "../types";

const RANGES = ["1", "7", "30", "90", "365"] as const;

export function CoinPage() {
  const { id = "" } = useParams();
  const { has, toggle } = useWatchlist();
  const [coin, setCoin] = useState<CoinDetail | null>(null);
  const [points, setPoints] = useState<ChartPoint[]>([]);
  const [days, setDays] = useState<(typeof RANGES)[number]>("7");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void fetchCoin(id)
      .then((data) => {
        if (!cancelled) setCoin(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Coin not found");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    void fetchChart(id, days)
      .then((data) => {
        if (!cancelled) setPoints(data);
      })
      .catch(() => {
        if (!cancelled) setPoints([]);
      });
    return () => {
      cancelled = true;
    };
  }, [id, days]);

  if (loading) {
    return <div className="hairline h-96 animate-pulse rounded-2xl bg-paper/50" />;
  }
  if (error || !coin) {
    return (
      <div className="hairline rounded-2xl p-8">
        <p className="font-medium">{error ?? "Coin not found"}</p>
        <Link to="/" className="mt-4 inline-block text-sm text-brand">
          Back to markets
        </Link>
      </div>
    );
  }

  const md = coin.market_data;
  const up = (md.price_change_percentage_7d ?? 0) >= 0;
  const description = coin.description.en.replace(/<[^>]+>/g, "").slice(0, 520);
  const saved = has(coin.id);

  return (
    <div className="flex flex-col gap-8">
      <Link to="/" className="text-sm text-mute hover:text-ink">
        ← Markets
      </Link>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <img src={coin.image.large} alt="" className="size-14 rounded-full" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{coin.name}</h1>
            <p className="font-mono text-sm uppercase text-mute">{coin.symbol}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="font-mono text-4xl tracking-tight">{formatUsd(md.current_price.usd)}</p>
          <PriceChange value={md.price_change_percentage_24h} />
        </div>
      </header>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => toggle(coin.id)}
          className={cn(
            "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm",
            saved ? "border-brand text-brand" : "border-white/10 text-mute hover:text-ink",
          )}
        >
          <Star className={cn("size-4", saved && "fill-brand")} />
          {saved ? "On watchlist" : "Add to watchlist"}
        </button>
        {coin.links.homepage[0] && (
          <a
            href={coin.links.homepage[0]}
            target="_blank"
            rel="noreferrer"
            className="rounded-full border border-white/10 px-4 py-2 text-sm text-mute hover:text-ink"
          >
            Website
          </a>
        )}
      </div>
      <section className="hairline rounded-2xl bg-paper/70 p-4 sm:p-6">
        <div className="mb-4 flex gap-2">
          {RANGES.map((range) => (
            <button
              key={range}
              type="button"
              onClick={() => setDays(range)}
              className={cn(
                "rounded-full px-3 py-1 font-mono text-xs text-mute",
                days === range && "bg-white/8 text-ink",
              )}
            >
              {range === "1" ? "1D" : range === "365" ? "1Y" : `${range}D`}
            </button>
          ))}
        </div>
        <PriceChart points={points} up={up} />
      </section>
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Market cap" value={formatUsd(md.market_cap.usd)} />
        <Stat label="Volume" value={formatUsd(md.total_volume.usd)} />
        <Stat label="ATH" value={formatUsd(md.ath.usd)} />
        <Stat label="Circ. supply" value={formatCompact(md.circulating_supply)} />
      </section>
      {description && (
        <section className="max-w-3xl text-sm leading-relaxed text-mute">
          {description}
          {coin.description.en.length > 520 ? "…" : ""}
        </section>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <article className="hairline rounded-2xl bg-paper/70 p-4">
      <p className="text-[11px] uppercase tracking-[0.16em] text-mute">{label}</p>
      <p className="mt-2 font-mono text-xl">{value}</p>
    </article>
  );
}
