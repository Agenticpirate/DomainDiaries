import { useEffect, useMemo, useState, type FormEvent } from "react";
import { fetchMarketsByIds, searchCoins } from "../lib/api";
import { formatQty, formatUsd } from "../lib/format";
import { usePortfolio } from "../hooks/usePortfolio";
import { PriceChange } from "../components/markets/PriceChange";
import type { Holding, MarketCoin, SearchCoin } from "../types";

export function PortfolioPage() {
  const { holdings, add, remove } = usePortfolio();
  const [quotes, setQuotes] = useState<MarketCoin[]>([]);
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<SearchCoin | null>(null);
  const [matches, setMatches] = useState<SearchCoin[]>([]);
  const [amount, setAmount] = useState("");
  const [cost, setCost] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!holdings.length) {
      setQuotes([]);
      return;
    }
    void fetchMarketsByIds(holdings.map((row) => row.id))
      .then(setQuotes)
      .catch(() => setQuotes([]));
  }, [holdings]);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 1) {
      setMatches([]);
      return;
    }
    const timer = window.setTimeout(() => {
      void searchCoins(trimmed).then((coins) => setMatches(coins.slice(0, 6)));
    }, 200);
    return () => window.clearTimeout(timer);
  }, [query]);

  const quoteMap = useMemo(() => new Map(quotes.map((coin) => [coin.id, coin])), [quotes]);
  const rows = holdings.map((holding) => {
    const quote = quoteMap.get(holding.id);
    const price = quote?.current_price ?? 0;
    const value = price * holding.amount;
    const pnl = value - holding.costUsd;
    const pnlPct = holding.costUsd > 0 ? (pnl / holding.costUsd) * 100 : null;
    return { holding, quote, value, pnl, pnlPct };
  });
  const totalValue = rows.reduce((sum, row) => sum + row.value, 0);
  const totalCost = holdings.reduce((sum, row) => sum + row.costUsd, 0);
  const totalPnl = totalValue - totalCost;
  const totalPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : null;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    if (!picked) {
      setFormError("Pick a coin from search first.");
      return;
    }
    const qty = Number(amount);
    const basis = Number(cost);
    if (!Number.isFinite(qty) || qty <= 0) {
      setFormError("Amount must be a positive number.");
      return;
    }
    if (!Number.isFinite(basis) || basis < 0) {
      setFormError("Cost basis must be zero or more.");
      return;
    }
    const holding: Holding = {
      id: picked.id,
      symbol: picked.symbol,
      name: picked.name,
      amount: qty,
      costUsd: basis,
    };
    add(holding);
    setPicked(null);
    setQuery("");
    setAmount("");
    setCost("");
    setMatches([]);
  }

  return (
    <div className="flex flex-col gap-8">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
        <p className="mt-2 text-mute">Holdings live in localStorage. Clearing site data wipes the book.</p>
      </header>
      <section className="grid gap-3 sm:grid-cols-3">
        <article className="hairline rounded-2xl bg-paper/70 p-4">
          <p className="text-[11px] uppercase tracking-[0.16em] text-mute">Value</p>
          <p className="mt-2 font-mono text-2xl">{formatUsd(totalValue)}</p>
        </article>
        <article className="hairline rounded-2xl bg-paper/70 p-4">
          <p className="text-[11px] uppercase tracking-[0.16em] text-mute">Cost</p>
          <p className="mt-2 font-mono text-2xl">{formatUsd(totalCost)}</p>
        </article>
        <article className="hairline rounded-2xl bg-paper/70 p-4">
          <p className="text-[11px] uppercase tracking-[0.16em] text-mute">P&L</p>
          <p className="mt-2 font-mono text-2xl">{formatUsd(totalPnl)}</p>
          <PriceChange value={totalPct} />
        </article>
      </section>
      <form onSubmit={onSubmit} className="hairline rounded-2xl bg-paper/70 p-5">
        <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-mute">Add holding</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <div className="relative md:col-span-2">
            <label htmlFor="coin" className="sr-only">
              Coin
            </label>
            <input
              id="coin"
              value={picked ? `${picked.name} (${picked.symbol.toUpperCase()})` : query}
              onChange={(event) => {
                setPicked(null);
                setQuery(event.target.value);
              }}
              placeholder="Search coin"
              className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 outline-none focus:border-white/30"
            />
            {matches.length > 0 && !picked && (
              <ul className="absolute z-10 mt-1 w-full overflow-hidden rounded-xl border border-white/10 bg-[#0e0e10]">
                {matches.map((coin) => (
                  <li key={coin.id}>
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-white/5"
                      onClick={() => {
                        setPicked(coin);
                        setQuery("");
                        setMatches([]);
                      }}
                    >
                      <img src={coin.thumb} alt="" className="size-5 rounded-full" />
                      {coin.name}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <label className="sr-only" htmlFor="amount">
            Amount
          </label>
          <input
            id="amount"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            placeholder="Amount"
            inputMode="decimal"
            className="rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 font-mono outline-none focus:border-white/30"
          />
          <label className="sr-only" htmlFor="cost">
            Cost basis USD
          </label>
          <input
            id="cost"
            value={cost}
            onChange={(event) => setCost(event.target.value)}
            placeholder="Cost basis USD"
            inputMode="decimal"
            className="rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 font-mono outline-none focus:border-white/30"
          />
        </div>
        {formError && <p className="mt-3 text-sm text-down">{formError}</p>}
        <button type="submit" className="mt-4 rounded-full bg-brand px-5 py-2 text-sm font-semibold text-black">
          Save holding
        </button>
      </form>
      {rows.length === 0 ? (
        <p className="text-sm text-mute">No positions yet. Add a holding to see live P&L.</p>
      ) : (
        <div className="hairline overflow-x-auto rounded-2xl bg-paper/70">
          <table className="min-w-[720px] w-full text-left">
            <thead className="text-[11px] uppercase tracking-[0.16em] text-mute">
              <tr className="border-b border-white/8">
                <th className="px-4 py-3 font-medium">Asset</th>
                <th className="px-4 py-3 text-right font-medium">Qty</th>
                <th className="px-4 py-3 text-right font-medium">Price</th>
                <th className="px-4 py-3 text-right font-medium">Value</th>
                <th className="px-4 py-3 text-right font-medium">P&L</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {rows.map(({ holding, quote, value, pnlPct }) => (
                <tr key={holding.id} className="border-b border-white/5">
                  <td className="px-4 py-3">
                    <span className="font-medium">{holding.name}</span>{" "}
                    <span className="font-mono text-xs uppercase text-mute">{holding.symbol}</span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-sm">{formatQty(holding.amount)}</td>
                  <td className="px-4 py-3 text-right font-mono text-sm">
                    {formatUsd(quote?.current_price ?? null)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-sm">{formatUsd(value)}</td>
                  <td className="px-4 py-3 text-right">
                    <PriceChange value={pnlPct} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => remove(holding.id)}
                      className="text-sm text-mute hover:text-down"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
