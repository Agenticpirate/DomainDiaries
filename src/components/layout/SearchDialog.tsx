import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { searchCoins } from "../../lib/api";
import type { SearchCoin } from "../../types";

type Props = {
  open: boolean;
  onClose: () => void;
};

export function SearchDialog({ open, onClose }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchCoin[]>([]);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setResults([]);
    const id = requestAnimationFrame(() => inputRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const trimmed = query.trim();
  useEffect(() => {
    if (!open || trimmed.length < 1) {
      setResults([]);
      return;
    }
    const timer = window.setTimeout(() => {
      setBusy(true);
      void searchCoins(trimmed)
        .then((coins) => setResults(coins.slice(0, 8)))
        .catch(() => setResults([]))
        .finally(() => setBusy(false));
    }, 220);
    return () => window.clearTimeout(timer);
  }, [open, trimmed]);

  const empty = useMemo(() => open && trimmed.length > 0 && !busy && results.length === 0, [open, trimmed, busy, results.length]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 grid place-items-start bg-black/70 px-4 pt-[12vh]" onClick={onClose}>
      <div
        className="w-full max-w-xl overflow-hidden rounded-2xl border border-white/10 bg-[#0e0e10] shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <label className="sr-only" htmlFor="krypto-search">
          Search coins
        </label>
        <input
          id="krypto-search"
          ref={inputRef}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search bitcoin, eth, sol…"
          className="w-full border-b border-white/8 bg-transparent px-5 py-4 font-mono text-lg outline-none"
        />
        <div className="max-h-80 overflow-y-auto p-2">
          {busy && <p className="px-3 py-4 text-sm text-mute">Searching…</p>}
          {empty && <p className="px-3 py-4 text-sm text-mute">No coins matched that query.</p>}
          {results.map((coin) => (
            <button
              key={coin.id}
              type="button"
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left hover:bg-white/5"
              onClick={() => {
                navigate(`/coin/${coin.id}`);
                onClose();
              }}
            >
              <img src={coin.thumb} alt="" className="size-7 rounded-full" />
              <span className="flex-1 font-medium">{coin.name}</span>
              <span className="font-mono text-xs uppercase text-mute">{coin.symbol}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
