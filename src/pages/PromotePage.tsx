import { useState } from "react";
import { useDirectory } from "../context/DirectoryContext";
import { OutbidDialog } from "../components/listings/OutbidDialog";
import { formatUsd } from "../lib/format";

export function PromotePage() {
  const { projects, outbid } = useDirectory();
  const [open, setOpen] = useState(false);
  const topBid = (projects[0]?.bidUsd ?? 17005) + 1;
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--violet)]">Promote</p>
      <h1 className="font-display mt-3 text-5xl font-bold">Buy the rank. Keep the aura.</h1>
      <p className="mt-4 text-lg text-[var(--mute)]">
        Krypto Directory is an auction for attention. Gold, silver, and bronze are not badges you mint — they are
        bids you defend.
      </p>
      <ul className="mt-8 flex flex-col gap-4 text-[var(--mute)]">
        <li>Podium cards on the home tape.</li>
        <li>Network and category leaderboards.</li>
        <li>Live outbid ticker for every raise.</li>
      </ul>
      <p className="mt-8 font-display text-3xl">
        Current #1 is {formatUsd(topBid - 1)}. Take it for {formatUsd(topBid)}.
      </p>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-8 rounded-full bg-gradient-to-r from-[#ff4d9d] to-[#ff8a4c] px-6 py-3 font-bold text-white"
      >
        List Your Project
      </button>
      <OutbidDialog
        open={open}
        defaultAmount={topBid}
        onClose={() => setOpen(false)}
        onSubmit={(input) => {
          outbid(input);
          setOpen(false);
        }}
      />
    </div>
  );
}
