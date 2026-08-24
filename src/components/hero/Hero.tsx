import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { PROJECTS_ONLINE, SPENT_24H } from "../../data/directory";
import { formatUsd, formatUsdExact } from "../../lib/format";
import { CATEGORIES } from "../../data/directory";
import type { CategoryId } from "../../types";
import { CoinOrbit } from "./CoinOrbit";

gsap.registerPlugin(useGSAP);

type Props = {
  topBid: number;
  url: string;
  category: CategoryId;
  onUrl: (value: string) => void;
  onCategory: (value: CategoryId) => void;
  onOutbid: () => void;
};

export function Hero({ topBid, url, category, onUrl, onCategory, onOutbid }: Props) {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(
    () => {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      gsap.from(".hero-copy > *", { y: 18, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out" });
    },
    { scope: root },
  );

  return (
    <section ref={root} className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
      <div className="hero-copy">
        <p className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] bg-black/20 px-3 py-1 text-xs text-[var(--mute)]">
          <span className="live-dot size-1.5 rounded-full bg-[var(--green)]" />
          {PROJECTS_ONLINE} projects online
          <span className="text-[var(--line)]">|</span>
          {formatUsdExact(SPENT_24H)} spent in the last 24h
        </p>
        <h1 className="font-display mt-5 text-4xl font-bold tracking-tight sm:text-6xl">
          Claim #1 in Crypto for{" "}
          <span className="bg-gradient-to-r from-[#ff4d9d] to-[#ff8a4c] bg-clip-text text-transparent">
            {formatUsd(topBid)}
          </span>
        </h1>
        <p className="mt-4 max-w-xl text-lg text-[var(--mute)]">
          A paid leaderboard for serious crypto products. Outbid the tape, own the podium, keep the clicks.
        </p>
        <form
          className="glass mt-8 flex flex-col gap-2 rounded-full p-2 sm:flex-row sm:items-center"
          onSubmit={(event) => {
            event.preventDefault();
            onOutbid();
          }}
        >
          <label className="sr-only" htmlFor="project-url">
            Project URL
          </label>
          <input
            id="project-url"
            value={url}
            onChange={(event) => onUrl(event.target.value)}
            placeholder="Enter your project URL"
            className="min-w-0 flex-1 rounded-full bg-transparent px-4 py-3 text-sm outline-none"
          />
          <label className="sr-only" htmlFor="hero-category">
            Category
          </label>
          <select
            id="hero-category"
            value={category}
            onChange={(event) => onCategory(event.target.value as CategoryId)}
            className="rounded-full bg-black/20 px-3 py-3 text-sm outline-none"
          >
            {CATEGORIES.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
          <button
            type="submit"
            className="rounded-full bg-gradient-to-r from-[#ff4d9d] to-[#ff5d6c] px-6 py-3 text-sm font-bold text-white shadow-[0_12px_30px_rgba(255,77,157,0.35)]"
          >
            Outbid
          </button>
        </form>
      </div>
      <CoinOrbit />
    </section>
  );
}
