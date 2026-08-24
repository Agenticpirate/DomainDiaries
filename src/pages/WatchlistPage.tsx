import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchMarketsByIds } from "../lib/api";
import { useWatchlist } from "../hooks/useWatchlist";
import { MarketsTable } from "../components/markets/MarketsTable";
import type { MarketCoin } from "../types";

export function WatchlistPage() {
  const { ids, toggle } = useWatchlist();
  const [coins, setCoins] = useState<MarketCoin[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ids.length) {
      setCoins([]);
      return;
    }
    setLoading(true);
    void fetchMarketsByIds(ids)
      .then(setCoins)
      .catch(() => setCoins([]))
      .finally(() => setLoading(false));
  }, [ids]);

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Watchlist</h1>
        <p className="mt-2 text-mute">Stars are stored in this browser only.</p>
      </header>
      {!ids.length && (
        <div className="hairline rounded-2xl p-8">
          <p className="font-medium">Nothing on the tape yet.</p>
          <p className="mt-2 text-sm text-mute">Open markets and star a name to pin it here.</p>
          <Link to="/" className="mt-4 inline-block text-sm text-brand">
            Browse markets
          </Link>
        </div>
      )}
      {loading && <div className="hairline h-48 animate-pulse rounded-2xl bg-paper/50" />}
      {!loading && coins.length > 0 && (
        <MarketsTable coins={coins} watched={ids} onToggleWatch={toggle} />
      )}
    </div>
  );
}
