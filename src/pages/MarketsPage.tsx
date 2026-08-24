import { useEffect, useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { fetchFearGreed, fetchGlobal } from "../lib/api";
import { useMarkets } from "../hooks/useMarkets";
import { useWatchlist } from "../hooks/useWatchlist";
import { MarketsTable } from "../components/markets/MarketsTable";
import { StatStrip } from "../components/markets/StatStrip";
import type { FearGreed, GlobalMarket } from "../types";

gsap.registerPlugin(useGSAP);

export function MarketsPage() {
  const root = useRef<HTMLDivElement>(null);
  const { coins, error, loading, reload } = useMarkets();
  const { ids, toggle } = useWatchlist();
  const [global, setGlobal] = useState<GlobalMarket | null>(null);
  const [fng, setFng] = useState<FearGreed | null>(null);

  useEffect(() => {
    void fetchGlobal().then(setGlobal).catch(() => setGlobal(null));
    void fetchFearGreed().then(setFng).catch(() => setFng(null));
  }, []);

  useGSAP(
    () => {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (reduce) return;
      gsap.from(".hero-copy, .stat-card", {
        y: 16,
        opacity: 0,
        duration: 0.55,
        stagger: 0.06,
        ease: "power2.out",
      });
    },
    { scope: root },
  );

  return (
    <div ref={root} className="flex flex-col gap-8">
      <section className="hero-copy max-w-3xl">
        <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/10 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-mute">
          <span className="size-1.5 animate-pulse rounded-full bg-brand" />
          Live desk · no login
        </p>
        <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
          The book stays on this machine.
        </h1>
        <p className="mt-4 max-w-xl text-lg text-mute">
          Watch the tape, star names you care about, and keep a private portfolio in the browser.
          Krypto never opens an account for you.
        </p>
      </section>
      <StatStrip global={global} fng={fng} />
      {loading && (
        <div className="hairline h-80 animate-pulse rounded-2xl bg-paper/50" aria-live="polite">
          <span className="sr-only">Loading markets</span>
        </div>
      )}
      {error && (
        <div className="hairline rounded-2xl p-6">
          <p className="font-medium">Markets did not load</p>
          <p className="mt-1 text-sm text-mute">{error}</p>
          <button
            type="button"
            onClick={() => void reload()}
            className="mt-4 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-black"
          >
            Retry
          </button>
        </div>
      )}
      {!loading && !error && <MarketsTable coins={coins} watched={ids} onToggleWatch={toggle} />}
    </div>
  );
}
