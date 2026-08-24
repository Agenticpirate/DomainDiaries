import type { ChartPoint, CoinDetail, FearGreed, GlobalMarket, MarketCoin, SearchCoin } from "../types";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  const data: unknown = await response.json();
  if (!response.ok) {
    const message =
      typeof data === "object" && data && "error" in data
        ? String((data as { error: string }).error)
        : "Request failed";
    throw new Error(message);
  }
  return data as T;
}

export function fetchMarkets(page = 1): Promise<MarketCoin[]> {
  return getJson<MarketCoin[]>(`/api/markets?page=${page}&per_page=100`);
}

export function fetchMarketsByIds(ids: string[]): Promise<MarketCoin[]> {
  if (!ids.length) return Promise.resolve([]);
  return getJson<MarketCoin[]>(`/api/markets?ids=${encodeURIComponent(ids.join(","))}&per_page=100`);
}

export function fetchGlobal(): Promise<GlobalMarket> {
  return getJson<GlobalMarket>("/api/global");
}

export function fetchFearGreed(): Promise<FearGreed> {
  return getJson<FearGreed>("/api/fng");
}

export async function searchCoins(query: string): Promise<SearchCoin[]> {
  const data = await getJson<{ coins: SearchCoin[] }>(`/api/search?q=${encodeURIComponent(query)}`);
  return data.coins ?? [];
}

export function fetchCoin(id: string): Promise<CoinDetail> {
  return getJson<CoinDetail>(`/api/coin/${id}`);
}

export async function fetchChart(id: string, days: string): Promise<ChartPoint[]> {
  const data = await getJson<{ prices: ChartPoint[] }>(`/api/chart/${id}?days=${days}`);
  return data.prices ?? [];
}
