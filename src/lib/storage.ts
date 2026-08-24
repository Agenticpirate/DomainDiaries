import type { Holding } from "../types";

const WATCH_KEY = "krypto.watchlist";
const HOLD_KEY = "krypto.portfolio";

function readJson<T>(key: string, fallback: T): T {
  if (typeof localStorage === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function loadWatchlist(): string[] {
  const ids = readJson<string[]>(WATCH_KEY, []);
  return Array.from(new Set(ids.filter((id) => typeof id === "string")));
}

export function saveWatchlist(ids: string[]): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(WATCH_KEY, JSON.stringify(ids));
}

export function loadHoldings(): Holding[] {
  const rows = readJson<Holding[]>(HOLD_KEY, []);
  return rows.filter(
    (row) => row && typeof row.id === "string" && typeof row.amount === "number" && row.amount > 0,
  );
}

export function saveHoldings(rows: Holding[]): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(HOLD_KEY, JSON.stringify(rows));
}
