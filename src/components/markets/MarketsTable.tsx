import { Star } from "lucide-react";
import { Link } from "react-router-dom";
import { formatCompact, formatUsd } from "../../lib/format";
import { cn } from "../../lib/cn";
import type { MarketCoin } from "../../types";
import { PriceChange } from "./PriceChange";
import { Sparkline } from "./Sparkline";

type Props = {
  coins: MarketCoin[];
  watched: string[];
  onToggleWatch: (id: string) => void;
};

export function MarketsTable({ coins, watched, onToggleWatch }: Props) {
  return (
    <div className="hairline overflow-hidden rounded-2xl bg-paper/70">
      <div className="overflow-x-auto">
        <table className="min-w-[860px] w-full border-collapse text-left">
          <thead className="text-[11px] uppercase tracking-[0.16em] text-mute">
            <tr className="border-b border-white/8">
              <th className="px-3 py-3 font-medium"> </th>
              <th className="px-2 py-3 font-medium">#</th>
              <th className="px-3 py-3 font-medium">Asset</th>
              <th className="px-3 py-3 text-right font-medium">Price</th>
              <th className="px-3 py-3 text-right font-medium">1h</th>
              <th className="px-3 py-3 text-right font-medium">24h</th>
              <th className="px-3 py-3 text-right font-medium">7d</th>
              <th className="px-3 py-3 text-right font-medium">Mkt cap</th>
              <th className="px-3 py-3 text-right font-medium">Last 7d</th>
            </tr>
          </thead>
          <tbody>
            {coins.map((coin) => {
              const up7 = (coin.price_change_percentage_7d_in_currency ?? 0) >= 0;
              const saved = watched.includes(coin.id);
              return (
                <tr key={coin.id} className="border-b border-white/5 hover:bg-white/3">
                  <td className="px-3 py-3">
                    <button
                      type="button"
                      aria-label={saved ? `Remove ${coin.name} from watchlist` : `Watch ${coin.name}`}
                      onClick={() => onToggleWatch(coin.id)}
                      className={cn("text-mute hover:text-brand", saved && "text-brand")}
                    >
                      <Star className={cn("size-4", saved && "fill-brand")} />
                    </button>
                  </td>
                  <td className="px-2 py-3 font-mono text-sm text-mute">{coin.market_cap_rank ?? "—"}</td>
                  <td className="px-3 py-3">
                    <Link to={`/coin/${coin.id}`} className="flex items-center gap-3">
                      <img src={coin.image} alt="" className="size-7 rounded-full" />
                      <span className="font-medium">{coin.name}</span>
                      <span className="font-mono text-xs uppercase text-mute">{coin.symbol}</span>
                    </Link>
                  </td>
                  <td className="px-3 py-3 text-right font-mono text-sm">{formatUsd(coin.current_price)}</td>
                  <td className="px-3 py-3 text-right">
                    <PriceChange value={coin.price_change_percentage_1h_in_currency} />
                  </td>
                  <td className="px-3 py-3 text-right">
                    <PriceChange value={coin.price_change_percentage_24h_in_currency} />
                  </td>
                  <td className="px-3 py-3 text-right">
                    <PriceChange value={coin.price_change_percentage_7d_in_currency} />
                  </td>
                  <td className="px-3 py-3 text-right font-mono text-sm text-mute">
                    {formatCompact(coin.market_cap)}
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex justify-end">
                      <Sparkline prices={coin.sparkline_in_7d?.price} up={up7} />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
