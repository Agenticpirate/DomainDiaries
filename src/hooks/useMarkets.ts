import { useCallback, useEffect, useState } from "react";
import { fetchMarkets } from "../lib/api";
import type { MarketCoin } from "../types";

export function useMarkets() {
  const [coins, setCoins] = useState<MarketCoin[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMarkets(1);
      setCoins(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load markets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { coins, error, loading, reload };
}
